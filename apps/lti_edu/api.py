from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from entity.api import BaseEntityListView, BaseEntityDetailView
from issuer.models import BadgeClass
from lti_edu.models import StudentsEnrolled, BadgeClassLtiContext, UserCurrentContextId
from lti_edu.serializers import StudentsEnrolledSerializerWithRelations, BadgeClassLtiContextSerializer, \
    BadgeClassLtiContextStudentSerializer
from mainsite.exceptions import BadgrApiException400, BadgrValidationError
from mainsite.permissions import AuthenticatedWithVerifiedEmail
from mainsite.utils import EmailMessageMaker
from staff.permissions import HasObjectPermission


class StudentEnrollmentList(BaseEntityListView):
    """
    GET a list of enrollments for a student
    DELETE for a student to delete your own enrollment
    """
    permission_classes = (AuthenticatedWithVerifiedEmail,)
    model = StudentsEnrolled
    serializer_class = StudentsEnrolledSerializerWithRelations
    http_method_names = ['get', 'delete']

    def get_objects(self, request, **kwargs):
        return StudentsEnrolled.objects.filter(user=request.user)

    def get(self, request, **kwargs):
        return super(StudentEnrollmentList, self).get(request, **kwargs)

    def delete(self, request, **kwargs):
        try:
            enrollment = StudentsEnrolled.objects.get(entity_id=request.data['enrollmentID'])
        except ValueError:
            raise BadgrApiException400("Invalid enrollment id", 204)
        except StudentsEnrolled.DoesNotExist:
            raise BadgrApiException400("Enrollment not found", 205)
        else:
            if enrollment.date_awarded:
                raise BadgrApiException400("Awarded enrollments cannot be withdrawn", 206)
            if request.user == enrollment.user:
                enrollment.delete()
                return Response(data='Enrollment withdrawn', status=200)
            else:
                raise BadgrApiException400("Users can only withdraw their own enrollments", 207)


class StudentsEnrolledList(BaseEntityListView):
    """
    POST: for a student to enroll himself
    """
    permission_classes = (AuthenticatedWithVerifiedEmail,)
    model = StudentsEnrolled
    http_method_names = ['post']

    def post(self, request, **kwargs):
        if 'badgeclass_slug' not in request.data:
            raise BadgrApiException400("Missing badgeclass id", 208)
        badge_class = get_object_or_404(BadgeClass, entity_id=request.data['badgeclass_slug'])
        if not badge_class.terms_accepted(request.user):
            raise BadgrValidationError("Cannot enroll, must accept terms first", 0)
        if request.user.may_enroll(badge_class, raise_exception=True):
            enrollment = StudentsEnrolled.objects.create(
                badge_class_id=badge_class.pk,
                user=request.user,
                date_consent_given=timezone.now()
            )
            # Clear cache for the enrollments of this badgeclass
            badge_class.remove_cached_data(['cached_pending_enrollments'])
            badge_class.remove_cached_data(['cached_pending_enrollments_including_denied'])
            message = EmailMessageMaker.create_student_badge_request_email(request.user, badge_class)
            request.user.email_user(subject='You have successfully requested an edubadge', html_message=message)
            return Response(data={'status': 'enrolled', 'entity_id': enrollment.entity_id}, status=201)
        raise BadgrApiException400('Cannot enroll', 209)


class EnrollmentDetail(BaseEntityDetailView):
    """
    PUT: update enrollment
    """
    permission_classes = (AuthenticatedWithVerifiedEmail, HasObjectPermission)
    permission_map = {'PUT': 'may_award'}
    model = StudentsEnrolled
    http_method_names = ['put']

    def put(self, request, **kwargs):
        enrollment = self.get_object(request, **kwargs)
        if not self.has_object_permissions(request, enrollment):
            raise BadgrApiException400("You do not have permission", 210)
        if enrollment.denied:
            raise BadgrApiException400("Enrollment already denied", 211)
        if enrollment.badge_instance:
            raise BadgrApiException400("Awarded enrollments cannot be denied", 212)
        enrollment.denied = True
        enrollment.save()
        html_message = EmailMessageMaker.create_enrollment_denied_email(enrollment)
        subject = 'Your request for the badgeclass {} has been denied by the issuer.'.format(
            enrollment.badge_class.name)
        enrollment.user.email_user(subject=subject, html_message=html_message)
        # Clear cache for the enrollments of this badgeclass
        enrollment.badge_class.remove_cached_data(['cached_pending_enrollments'])
        enrollment.badge_class.remove_cached_data(['cached_pending_enrollments_including_denied'])
        return Response(data='Succesfully denied enrollment', status=HTTP_200_OK)


class BadgeClassLtiContextListView(BaseEntityListView):
    permission_classes = (AuthenticatedWithVerifiedEmail,)
    model = BadgeClassLtiContext
    serializer_class = BadgeClassLtiContextSerializer

    def get_objects(self, request, **kwargs):
        if 'lti_context_id' in kwargs:
            lti_context_id = kwargs['lti_context_id']
            badgeclasses_per_context_id = BadgeClassLtiContext.objects.filter(context_id=lti_context_id).all()
            return badgeclasses_per_context_id
        return []


class BadgeClassLtiContextStudentListView(BaseEntityListView):
    permission_classes = (AuthenticatedWithVerifiedEmail,)
    model = BadgeClassLtiContext
    serializer_class = BadgeClassLtiContextStudentSerializer

    def get_objects(self, request, **kwargs):
        if 'lti_context_id' in kwargs:
            lti_context_id = kwargs['lti_context_id']
            badgeclasses_per_context_id = BadgeClassLtiContext.objects.filter(context_id=lti_context_id).all()
            return badgeclasses_per_context_id
        return []


class BadgeClassLtiContextDetailView(BaseEntityDetailView):
    permission_classes = (AuthenticatedWithVerifiedEmail,)
    model = BadgeClassLtiContext
    serializer_class = BadgeClassLtiContextSerializer

    def post(self, request, **kwargs):
        context_id = request.data['contextId']
        badge_class = BadgeClass.objects.get(entity_id=request.data['badgeClassEntityId'])
        BadgeClassLtiContext.objects.get_or_create(context_id=context_id, badge_class=badge_class)
        message = 'Succesfully added badgeclass'
        return Response(data=message, status=HTTP_200_OK)

    def delete(self, request, **kwargs):
        context_id = request.data['contextId']
        badge_class = BadgeClass.objects.get(entity_id=request.data['badgeClassEntityId'])
        BadgeClassLtiContext.objects.get(context_id=context_id, badge_class=badge_class).delete()
        message = 'Succesfully deleted badgeclass'
        return Response(data=message, status=HTTP_200_OK)


class CurrentContextView(BaseEntityDetailView):
    permission_classes = (AuthenticatedWithVerifiedEmail,)

    def get(self, request, **kwargs):
        response = {'loggedin': True,
                    'lticontext': None}
        if not request.user.is_authenticated:
            response['loggedin'] = False
        else:
            try:
                user_current_context_id = UserCurrentContextId.objects.get(badge_user=request.user)
                response['lticontext'] = user_current_context_id.context_id
            except Exception as e:
                pass

        return JsonResponse(response)
