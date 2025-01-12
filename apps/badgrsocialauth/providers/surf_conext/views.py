import datetime
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

import requests
from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.socialaccount.helpers import render_authentication_error, complete_social_login
from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from jose import jwt

from badgeuser.models import UserProvisionment
from badgrsocialauth.utils import set_session_badgr_app, get_session_authcode, get_verified_user, get_social_account, \
    AuthErrorCode
from ims.models import LTITenant
from institution.models import Institution
from lti_edu.models import LtiBadgeUserTennant, UserCurrentContextId
from mainsite.exceptions import BadgrValidationError
from mainsite.models import BadgrApp
from .provider import SurfConextProvider

logger = logging.getLogger('Badgr.Debug')

def login(request):
    """
    Redirect to login page of SURFconext openID, this is "Where are you from" page
    :return: HTTP redirect to WAYF
    """
    lti_data = request.session.get('lti_data', None)
    lti_context_id = ''
    lti_user_id = ''
    lti_roles = ''
    if lti_data is not None:
        lti_context_id = lti_data['lti_context_id']
        lti_user_id = lti_data['lti_user_id']
        lti_roles = lti_data['lti_roles']

    _current_app = SocialApp.objects.get_current(provider='surf_conext')

    # state contains the data required for the redirect after the login via SURFconext,
    # it contains the user token, type of process and which badge_app

    referer = request.META['HTTP_REFERER'].split('/')[3]
    badgr_app_pk = request.session.get('badgr_app_pk', None)
    try:
        badgr_app_pk = int(badgr_app_pk)
    except:
        badgr_app_pk = settings.BADGR_APP_ID
    state = json.dumps([request.GET.get('process', 'login'),
                        get_session_authcode(request),
                        badgr_app_pk,
                        lti_context_id,
                        lti_user_id,
                        lti_roles,
                        referer])

    params = {
        "state": state,
        "client_id": _current_app.client_id,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": f"{settings.HTTP_ORIGIN}/account/openid/login/callback/",
        "claims": "{\"id_token\":{\"preferred_username\":null,\"given_name\":null,"
                  "\"family_name\":null,\"email\":null,\"schac_home_organization\":null}}"
    }
    args = urllib.parse.urlencode(params)
    # Redirect to eduID and enforce a linked SURFconext user with validated names
    login_url = f"{settings.SURFCONEXT_DOMAIN_URL}/authorize?{args}"
    return redirect(login_url)


@csrf_exempt
def callback(request):
    """
        Callback page, after user returns from "Where are you from" page.

        Steps:
        1. Exchange callback Token for id token
        2. Decode id_token with the user info in the claims
        3. Complete social login and return to frontend

        Retrieved information:
        - email: required, if not available will fail request
        - sub: required, string, user code
        - given_name: optional, string
        - family_name: optional, string
        - schac_home_organization: required

    :return: Either renders authentication error, or completes the social login
    """
    # extract the state of the redirect
    if request.user.is_authenticated:
        get_account_adapter(request).logout(request)  # logging in while being authenticated breaks the login procedure

    process, auth_token, badgr_app_pk, lti_data, lti_user_id, lti_roles, referer = json.loads(request.GET.get('state'))

    code = request.GET.get('code', None)
    if code is None:
        error = 'Server error: No userToken found in callback'
        return render_authentication_error(request, SurfConextProvider.id, error=error)

    # 1. Exchange callback Token for id token
    _current_app = SocialApp.objects.get_current(provider='surf_conext')
    payload = {
        "grant_type": "authorization_code",
        "redirect_uri": f"{settings.HTTP_ORIGIN}/account/openid/login/callback/",
        "code": code,
        "scope": "openid",
        "client_id": _current_app.client_id,
        "client_secret": _current_app.secret,
    }
    headers = {'Content-Type': "application/x-www-form-urlencoded",
               'Cache-Control': "no-cache"
               }
    response = requests.post(f"{settings.SURFCONEXT_DOMAIN_URL}/token", data=urllib.parse.urlencode(payload),
                             headers=headers)

    if response.status_code != 200:
        error = 'Server error: Token endpoint error (http %s) try alternative login methods' % response.status_code
        return render_authentication_error(request, SurfConextProvider.id, error=error)

    data = response.json()
    id_token = data.get('id_token', None)

    if id_token is None:
        error = 'Server error: No id_token token, try alternative login methods.'
        return render_authentication_error(request, SurfConextProvider.id, error=error)

    badgr_app = BadgrApp.objects.get(pk=badgr_app_pk)
    set_session_badgr_app(request, BadgrApp.objects.get(pk=badgr_app.pk))

    payload = jwt.get_unverified_claims(id_token)
    for attr in ['sub', 'email', 'schac_home_organization']:
        if attr not in payload:
            error = f"Sorry, your account does not have a {attr} attribute. Login with SURFconext and then try again"
            logger.error(error)
            return render_authentication_error(request, SurfConextProvider.id, error)

    # 3. Complete social login and return to frontend
    provider = SurfConextProvider(request)
    login = provider.sociallogin_from_response(request, payload)
    # connect process in which OpenID connects with, either login or connect, if you connect then login user with token
    login.state = {'process': process}
    # login for connect because socialLogin can only connect to request.user
    if process == 'connect' and request.user.is_anonymous and auth_token:
        request.user = get_verified_user(auth_token=auth_token)
    ret = complete_social_login(request, login)
    new_url = ret.url+'&role=teacher'
    ret = HttpResponseRedirect(new_url)

    if not request.user.is_anonymous:  # the social login succeeded
        institution_identifier = payload['schac_home_organization']
        try:
            institution = Institution.objects.get(identifier=institution_identifier)
            # the institution exists
            if request.user.invited:  # this user has been invited in the past
                provisions = request.user.match_provisionments()
                for provision in provisions:
                    provision.perform_provisioning()
            else:  # user has not been invited, check for invitations
                request.user.institution = institution
                request.user.is_teacher = True
                request.user.invited = True
                try:
                    provisionments = request.user.match_provisionments()
                    request.user.save()
                    for provisionment in provisionments:
                        provisionment.match_user(request.user)
                        provisionment.perform_provisioning()
                except (UserProvisionment.DoesNotExist, BadgrValidationError):  # there is no provisionment
                    extra_context = {}
                    if institution and institution.cached_staff():
                        cached_staff = institution.cached_staff()
                        admins = list(filter(lambda u: u.may_administrate_users, cached_staff))
                        if len(admins) > 0:
                            extra_context["admin_email"] = admins[0].user.email

                    error = 'Sorry, you can not register without an invite.'
                    extra_context["code"] = AuthErrorCode.REGISTER_WITHOUT_INVITE
                    if request.user.date_joined.today().date() == datetime.datetime.today().date():  # extra protection before deletion
                        request.user.delete()
                    return render_authentication_error(request, SurfConextProvider.id, error,
                                                       extra_context=extra_context)

        except Institution.DoesNotExist:  # no institution yet, and therefore also first login ever
            error = 'Sorry, your institution has not been created yet.'
            return render_authentication_error(request, SurfConextProvider.id, error,
                                               extra_context={"code": AuthErrorCode.REGISTER_WITHOUT_INVITE})

    request.user.accept_general_terms()

    lti_data = request.session.get('lti_data', None)
    if lti_data is not None and 'lti_user_id' in lti_data:
        if not request.user.is_anonymous:
            tenant = LTITenant.objects.get(client_key=lti_data['lti_tenant'])
            badgeuser_tennant, _ = LtiBadgeUserTennant.objects.get_or_create(lti_user_id=lti_data['lti_user_id'],
                                                                             badge_user=request.user,
                                                                             lti_tennant=tenant,
                                                                             staff=True)
            user_current_context_id, _ = UserCurrentContextId.objects.get_or_create(badge_user=request.user)
            user_current_context_id.context_id = lti_data['lti_context_id']
            user_current_context_id.save()

    request.session['lti_user_id'] = lti_user_id
    request.session['lti_roles'] = lti_roles
    # override the response with a redirect to staff dashboard if the login came from there
    if referer == 'staff':
        return HttpResponseRedirect(reverse('admin:index'))
    return ret
