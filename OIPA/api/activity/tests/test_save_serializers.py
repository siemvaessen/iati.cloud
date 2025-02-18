# TODO: no need to test codelist fields separately; instead test the whole
# serializer in once along with the code and vocabulary fields. Or is
# testing the fields separately preferable?

import datetime
from decimal import Decimal
from unittest import skip

from django.core.exceptions import ObjectDoesNotExist
# Runs each test in a transaction and flushes database
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from api.activity import serializers
from iati import models as iati_models
from iati.factory.iati_factory import (
    ActivityDateFactory, ActivityDateTypeFactory, ActivityFactory,
    ActivityPolicyMarkerFactory, ActivityRecipientCountryFactory,
    ActivityRecipientRegionFactory, ActivitySectorFactory, BudgetFactory,
    BudgetItemFactory, BudgetStatusFactory, BudgetTypeFactory,
    ConditionFactory, ConditionsFactory, ContactInfoFactory,
    ContactTypeFactory, CountryBudgetItemFactory, CountryFactory,
    CrsAddFactory, CrsAddOtherFlagsFactory, CurrencyFactory,
    DescriptionFactory, DescriptionTypeFactory, DocumentLinkCategoryFactory,
    DocumentLinkFactory, DocumentLinkLanguageFactory, FinanceTypeFactory,
    FlowTypeFactory, FssFactory, FssForecastFactory,
    GeographicExactnessFactory, GeographicLocationClassFactory,
    GeographicLocationReachFactory, GeographicVocabularyFactory,
    HumanitarianScopeFactory, HumanitarianScopeTypeFactory,
    HumanitarianScopeVocabularyFactory, IndicatorMeasureFactory,
    LegacyDataFactory, LoanRepaymentPeriodFactory, LoanRepaymentTypeFactory,
    LocationFactory, LocationTypeFactory, OrganisationFactory,
    OrganisationRoleFactory, OrganisationTypeFactory, OtherIdentifierFactory,
    ParticipatingOrganisationFactory, PlannedDisbursementFactory,
    PolicyMarkerFactory, PolicyMarkerVocabularyFactory,
    PolicySignificanceFactory, RegionFactory, RegionVocabularyFactory,
    RelatedActivityFactory, ResultFactory, ResultIndicatorFactory,
    ResultIndicatorPeriodTargetFactory, ResultIndicatorReferenceFactory,
    ResultTypeFactory, SectorFactory, SectorVocabularyFactory,
    TiedStatusFactory, TitleFactory
)
from iati.parser.exceptions import FieldValidationError
from iati.permissions.factories import (
    OrganisationAdminGroupFactory, OrganisationUserFactory
)
from iati.transaction import factories as transaction_factory
from iati.transaction import models as transaction_models
from iati_codelists.factory import codelist_factory
from iati_codelists.factory.codelist_factory import AidTypeFactory
from iati_vocabulary.factory import vocabulary_factory


class ErrorHandlingTestCase(TestCase):
    def test_handle_errors_raises_proper_dict(self):
        validated = {
            "errors": [
                FieldValidationError(
                    "Activity",
                    "id",
                    "required"
                ),
                FieldValidationError(
                    "Activity",
                    "name",
                    "required"
                ),
                FieldValidationError(
                    "Activity",
                    "description-nested",
                    "required",
                    apiField="description.nested"
                ),
            ],
            "validated_data": {
                "id": "test",
            }
        }

        try:
            serializers.handle_errors(validated)
            self.assertFail()
        except Exception as e:
            self.assertEqual(
                e.get_full_details(), {
                    'id': {
                        u'message': u'required',
                        u'code': u'invalid'
                    },
                    'description': {
                        'nested': {
                            u'message': u'required',
                            u'code': u'invalid'
                        }
                    },
                    'name': {
                        u'message': u'required',
                        u'code': u'invalid'
                    }
                })


class ActivitySaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    @skip
    def test_create_activity(self):

        iati_version = codelist_factory.VersionFactory.create(code="2.02")
        language = codelist_factory.LanguageFactory.create()
        activity_status = codelist_factory.ActivityStatusFactory.create()
        activity_scope = codelist_factory.ActivityScopeFactory.create()
        collaboration_type = codelist_factory.CollaborationTypeFactory.create()
        default_flow_type = codelist_factory.FlowTypeFactory.create()
        default_finance_type = codelist_factory.FinanceTypeFactory.create()
        default_aid_type = codelist_factory.AidTypeFactory.create()
        default_tied_status = codelist_factory.TiedStatusFactory.create()

        data = {
            "iati_identifier": 'IATI-0001',
            'iati_standard_version': {
                "code": iati_version.code,  # should be ignored
                "name": 'irrelevant',
            },
            "humanitarian": "1",
            'activity_status': {
                "code": activity_status.code,  # should be ignored
                "name": 'irrelevant',
            },
            'activity_scope': {
                "code": activity_scope.code,  # should be ignored
                "name": 'irrelevant',
            },
            'collaboration_type': {
                "code": collaboration_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_flow_type': {
                "code": default_flow_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_finance_type': {
                "code": default_finance_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_aid_type': {
                "code": default_aid_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_tied_status': {
                "code": default_tied_status.code,  # should be ignored
                "name": 'irrelevant',
            },
            "xml_lang": language.code,
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "capital_spend": Decimal("20.2"),
            "secondary_reporter": False,
        }

        res = self.c.post(
            "/api/publishers/{}/activities/?format=json".format(
                self.publisher.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Activity.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.iati_identifier, data['iati_identifier'])
        self.assertEqual(instance.iati_standard_version.code, "2.02")
        self.assertEqual(instance.humanitarian, bool(data['humanitarian']))
        self.assertEqual(instance.activity_status.code,
                         str(data['activity_status']['code']))
        self.assertEqual(instance.scope.code, str(
            data['activity_scope']['code']))
        self.assertEqual(instance.collaboration_type.code,
                         str(data['collaboration_type']['code']))
        self.assertEqual(instance.default_flow_type.code,
                         str(data['default_flow_type']['code']))
        self.assertEqual(
            instance.default_finance_type.code, str(
                data['default_finance_type']['code']))
        self.assertEqual(instance.default_aid_type.code,
                         str(data['default_aid_type']['code']))
        self.assertEqual(
            instance.default_tied_status.code, str(
                data['default_tied_status']['code']))
        self.assertEqual(instance.capital_spend, data['capital_spend'])
        self.assertEqual(instance.secondary_reporter,
                         data['secondary_reporter'])

        title = instance.title

        # order by creation time ('id')
        title_narratives = title.narratives.all().order_by('id')
        self.assertEqual(
            title_narratives[0].content,
            data['title']['narratives'][0]['text']
        )
        self.assertEqual(
            title_narratives[1].content,
            data['title']['narratives'][1]['text']
        )

    @skip
    def test_update_activity(self):
        activity = ActivityFactory.create()
        title = TitleFactory.create(activity=activity)

        iati_version = codelist_factory.VersionFactory.create(code="2.02")
        language = codelist_factory.LanguageFactory.create()
        activity_status = codelist_factory.ActivityStatusFactory.create()
        activity_scope = codelist_factory.ActivityScopeFactory.create()
        collaboration_type = codelist_factory.CollaborationTypeFactory.create()
        default_flow_type = codelist_factory.FlowTypeFactory.create()
        default_finance_type = codelist_factory.FinanceTypeFactory.create()
        default_aid_type = codelist_factory.AidTypeFactory.create()
        default_tied_status = codelist_factory.TiedStatusFactory.create()

        data = {
            "iati_identifier": 'IATI-0001',
            'iati_standard_version': {
                "code": iati_version.code,  # should be ignored
                "name": 'irrelevant',
            },
            "humanitarian": "1",
            'activity_status': {
                "code": activity_status.code,  # should be ignored
                "name": 'irrelevant',
            },
            'activity_scope': {
                "code": activity_scope.code,  # should be ignored
                "name": 'irrelevant',
            },
            'collaboration_type': {
                "code": collaboration_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_flow_type': {
                "code": default_flow_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_finance_type': {
                "code": default_finance_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_aid_type': {
                "code": default_aid_type.code,  # should be ignored
                "name": 'irrelevant',
            },
            'default_tied_status': {
                "code": default_tied_status.code,  # should be ignored
                "name": 'irrelevant',
            },
            "xml_lang": language.code,
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "capital_spend": Decimal("20.2"),
            "secondary_reporter": False,
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Activity.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.iati_identifier, data['iati_identifier'])
        self.assertEqual(instance.iati_standard_version.code, "2.02")
        self.assertEqual(instance.humanitarian, bool(data['humanitarian']))
        self.assertEqual(instance.activity_status.code,
                         str(data['activity_status']['code']))
        self.assertEqual(instance.scope.code, str(
            data['activity_scope']['code']))
        self.assertEqual(instance.collaboration_type.code,
                         str(data['collaboration_type']['code']))
        self.assertEqual(instance.default_flow_type.code,
                         str(data['default_flow_type']['code']))
        self.assertEqual(
            instance.default_finance_type.code, str(
                data['default_finance_type']['code']))
        self.assertEqual(instance.default_aid_type.code,
                         str(data['default_aid_type']['code']))
        self.assertEqual(
            instance.default_tied_status.code, str(
                data['default_tied_status']['code']))
        self.assertEqual(instance.capital_spend, data['capital_spend'])
        self.assertEqual(instance.secondary_reporter,
                         data['secondary_reporter'])

        title = instance.title

        # order by creation time ('id')
        title_narratives = title.narratives.all().order_by('id')

        self.assertEqual(
            title_narratives[0].content,
            data['title']['narratives'][0]['text']
        )
        self.assertEqual(
            title_narratives[1].content,
            data['title']['narratives'][1]['text']
        )

    def test_delete_activity(self):
        activity = ActivityFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/?format=json".format(
                self.publisher.id, activity.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Activity.objects.get(pk=activity.id)


@skip
class DescriptionSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_description(self):

        activity = ActivityFactory.create()
        type = DescriptionTypeFactory.create()

        data = {
            "activity": activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/descriptions/?format=json".format(  # NOQA: E501
            self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Description.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_update_description(self):
        description = DescriptionFactory.create()
        type = DescriptionTypeFactory.create()  # NOQA: F841
        type2 = DescriptionTypeFactory.create(code=2)

        data = {
            "activity": description.activity.id,
            "type": {
                "code": type2.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/descriptions/{}?format=json".format(  # NOQA: E501
                self.publisher.id, description.activity.id, description.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Description.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, str(data['type']['code']))

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_delete_description(self):
        description = DescriptionFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/descriptions/{}?format=json".format(  # NOQA: E501
                self.publisher.id, description.activity.id, description.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Description.objects.get(pk=description.id)


@skip
class ParticipatingOrganisationSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_participating_organisation(self):

        activity = ActivityFactory.create()
        organisation = OrganisationFactory.create()
        org_type = OrganisationTypeFactory.create(code=9)
        org_role = OrganisationRoleFactory.create(code=1)

        data = {
            "ref": 'GB-COH-03580586',
            "activity": activity.id,
            "organisation": organisation.organisation_identifier,
            "type": {
                "code": org_type.code,
                "name": 'irrelevant',
            },
            "role": {
                "code": org_role.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/participating_organisations/?format=json".format(  # NOQA: E501
            self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ActivityParticipatingOrganisation.objects\
            .get(pk=res.json()['id'])

        self.assertEqual(instance.ref, data['ref'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(
            instance.organisation.organisation_identifier, data['organisation']
        )
        self.assertEqual(instance.type.code, str(data['type']['code']))
        self.assertEqual(instance.role.code, str(data['role']['code']))

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_update_participating_organisation(self):
        participating_org = ParticipatingOrganisationFactory\
            .create()

        org_type = OrganisationTypeFactory.create(code=22)
        org_role = OrganisationRoleFactory.create(code=22)

        data = {
            "ref": 'GB-COH-03580586',
            "activity": participating_org.activity.id,
            "organisation": participating_org.organisation.organisation_identifier,  # NOQA: E501
            "type": {
                "code": org_type.code,
                "name": 'irrelevant',
            },
            "role": {
                "code": org_role.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/participating_organisations/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                participating_org.activity.id,
                participating_org.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ActivityParticipatingOrganisation.objects.get(
            ref=data['ref'])

        self.assertEqual(instance.ref, data['ref'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(
            instance.organisation.organisation_identifier,
            data['organisation']
        )
        self.assertEqual(instance.type.code, str(data['type']['code']))
        self.assertEqual(instance.role.code, str(data['role']['code']))

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_delete_participating_organisation(self):
        participating_org = ParticipatingOrganisationFactory\
            .create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/participating_organisations/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                participating_org.activity.id,
                participating_org.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ActivityParticipatingOrganisation.objects.get(
                pk=participating_org.id)


class ActivityDateSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    @skip
    def test_create_activity_date(self):

        activity = ActivityFactory.create()
        type = ActivityDateTypeFactory.create()

        data = {
            "activity": activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "iso_date": datetime.date.today().isoformat(),
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/activity_dates/?format=json".format(  # NOQA: E501
            self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ActivityDate.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])

    @skip
    def test_update_activity_date(self):
        activity_date = ActivityDateFactory.create()
        type = ActivityDateTypeFactory.create()  # NOQA: F841
        type2 = ActivityDateTypeFactory.create(code=2)

        data = {
            "activity": activity_date.activity.id,
            "type": {
                "code": type2.code,
                "name": 'irrelevant',
            },
            "iso_date": datetime.date.today().isoformat(),
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/activity_dates/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                activity_date.activity.id,
                activity_date.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ActivityDate.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, str(data['type']['code']))

    def test_delete_activity_dates(self):
        activity_dates = ActivityDateFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/activity_dates/{}?format=json".format(  # NOQA: E501
            self.publisher.id, activity_dates.activity.id, activity_dates.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ActivityDate.objects.get(
                pk=activity_dates.id)


@skip
class ContactInfoSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_contact_info(self):

        activity = ActivityFactory.create()
        contact_type = ContactTypeFactory.create()

        data = {
            "activity": activity.id,
            "type": {
                "code": contact_type.code,
                "name": "irrelevant"
            },
            "organisation": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "department": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "person_name": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "job_title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "telephone": "0631942897",
            "email": "test@zz.com",
            "website": "https://zimmerman.team",
            "mailing_address": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            }
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/contact_info/?format=json".format(  # NOQA: E501
            self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ContactInfo.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])

        # order by creation time ('id')
        organisation_narratives = instance.organisation.narratives.all()\
            .order_by('id')

        self.assertEqual(
            organisation_narratives[0].content,
            data['organisation']['narratives'][0]['text'])
        self.assertEqual(
            organisation_narratives[1].content,
            data['organisation']['narratives'][1]['text'])

        # order by creation time ('id')
        department_narratives = instance.department.narratives.all()\
            .order_by('id')

        self.assertEqual(
            department_narratives[0].content,
            data['department']['narratives'][0]['text'])
        self.assertEqual(
            department_narratives[1].content,
            data['department']['narratives'][1]['text'])

        # order by creation time ('id')
        person_name_narratives = instance.person_name.narratives.all()\
            .order_by('id')

        self.assertEqual(
            person_name_narratives[0].content,
            data['person_name']['narratives'][0]['text'])
        self.assertEqual(
            person_name_narratives[1].content,
            data['person_name']['narratives'][1]['text'])

        # order by creation time ('id')
        job_title_narratives = instance.job_title.narratives.all()\
            .order_by('id')

        self.assertEqual(
            job_title_narratives[0].content,
            data['job_title']['narratives'][0]['text'])
        self.assertEqual(
            job_title_narratives[1].content,
            data['job_title']['narratives'][1]['text'])

        # order by creation time ('id')
        mailing_address_narratives = instance.mailing_address.narratives.all()\
            .order_by('id')

        self.assertEqual(
            mailing_address_narratives[0].content,
            data['mailing_address']['narratives'][0]['text'])
        self.assertEqual(
            mailing_address_narratives[1].content,
            data['mailing_address']['narratives'][1]['text'])

    def test_update_contact_info(self):
        contact_info = ContactInfoFactory.create()
        contact_type = ContactTypeFactory.create()

        data = {
            "activity": contact_info.activity.id,
            "type": {
                "code": contact_type.code,
                "name": "irrelevant"
            },
            "organisation": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "department": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "person_name": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "job_title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "telephone": "0631942897",
            "email": "test@zz.com",
            "website": "https://zimmerman.team",
            "mailing_address": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            }
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/contact_info/{}?format=json".format(  # NOQA: E501
                self.publisher.id, contact_info.activity.id, contact_info.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ContactInfo.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])

        # order by creation time ('id')
        organisation_narratives = instance.organisation.narratives.all()\
            .order_by('id')

        self.assertEqual(
            organisation_narratives[0].content,
            data['organisation']['narratives'][0]['text'])
        self.assertEqual(
            organisation_narratives[1].content,
            data['organisation']['narratives'][1]['text'])

        # order by creation time ('id')
        department_narratives = instance.department.narratives.all()\
            .order_by('id')

        self.assertEqual(
            department_narratives[0].content,
            data['department']['narratives'][0]['text'])
        self.assertEqual(
            department_narratives[1].content,
            data['department']['narratives'][1]['text'])

        # order by creation time ('id')
        person_name_narratives = instance.person_name.narratives.all()\
            .order_by('id')

        self.assertEqual(
            person_name_narratives[0].content,
            data['person_name']['narratives'][0]['text'])
        self.assertEqual(
            person_name_narratives[1].content,
            data['person_name']['narratives'][1]['text'])

        # order by creation time ('id')
        job_title_narratives = instance.job_title.narratives.all()\
            .order_by('id')

        self.assertEqual(
            job_title_narratives[0].content,
            data['job_title']['narratives'][0]['text'])
        self.assertEqual(
            job_title_narratives[1].content,
            data['job_title']['narratives'][1]['text'])

        # order by creation time ('id')
        mailing_address_narratives = instance.mailing_address.narratives.all()\
            .order_by('id')

        self.assertEqual(
            mailing_address_narratives[0].content,
            data['mailing_address']['narratives'][0]['text'])
        self.assertEqual(
            mailing_address_narratives[1].content,
            data['mailing_address']['narratives'][1]['text'])

    def test_delete_contact_info(self):
        contact_infos = ContactInfoFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/contact_info/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                contact_infos.activity.id,
                contact_infos.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ContactInfo.objects.get(pk=contact_infos.id)


@skip
class ActivityRecipientCountrySaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_recipient_country(self):

        activity = ActivityFactory.create()
        country = CountryFactory.create()

        data = {
            "activity": activity.id,
            "country": {
                "code": country.code,
                "name": 'irrelevant',
            },
            "percentage": 100,
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/recipient_countries/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ActivityRecipientCountry.objects.get(
            pk=res.json()['id']
        )

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.country.code, data['country']['code'])
        self.assertEqual(instance.percentage, data['percentage'])

    def test_update_recipient_country(self):
        recipient_country = ActivityRecipientCountryFactory\
            .create()
        country = CountryFactory.create(code='AF')

        data = {
            "activity": recipient_country.activity.id,
            "country": {
                "code": country.code,
                "name": 'irrelevant',
            },
            "percentage": 100,
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/recipient_countries/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                recipient_country.activity.id,
                recipient_country.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ActivityRecipientCountry.objects.get(
            pk=res.json()['id']
        )

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.country.code, str(data['country']['code']))
        self.assertEqual(instance.percentage, data['percentage'])

    def test_delete_recipient_country(self):
        recipient_country = ActivityRecipientCountryFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/recipient_countries/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                recipient_country.activity.id,
                recipient_country.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ActivityRecipientCountry.objects.get(
                pk=recipient_country.id)


@skip
class ActivityRecipientRegionSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_recipient_region(self):

        activity = ActivityFactory.create()
        region = RegionFactory.create()
        region_vocabulary = RegionVocabularyFactory.create()

        data = {
            "activity": activity.id,
            "region": {
                "code": region.code,
                "name": 'irrelevant',
            },
            "vocabulary": {
                "code": region_vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://twitter.com/",
            "percentage": 100,
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/recipient_regions/?format=json".format(  # NOQA: E501
            self.publisher.id,
            activity.id
        ),
        data,
        format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ActivityRecipientRegion.objects.get(
            pk=res.json()['id']
        )

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.region.code, str(data['region']['code']))
        self.assertEqual(instance.percentage, data['percentage'])

    def test_update_recipient_region(self):
        recipient_region = ActivityRecipientRegionFactory.create()
        region = RegionFactory.create(code=89)

        data = {
            "activity": recipient_region.activity.id,
            "region": {
                "code": region.code,
                "name": 'irrelevant',
            },
            "vocabulary": {
                "code": recipient_region.vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://twitter.com/",
            "percentage": 100,
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/recipient_regions/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                recipient_region.activity.id,
                recipient_region.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ActivityRecipientRegion.objects.get(
            pk=res.json()['id']
        )

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.region.code, str(data['region']['code']))
        self.assertEqual(instance.vocabulary.code,
                         str(data['vocabulary']['code']))

    def test_delete_recipient_region(self):
        recipient_region = ActivityRecipientRegionFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/recipient_regions/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                recipient_region.activity.id,
                recipient_region.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ActivityRecipientRegion.objects.get(
                pk=recipient_region.id)


class ActivitySectorSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    @skip('NotImplemented')
    def test_create__sector(self):

        activity = ActivityFactory.create()
        sector = SectorFactory.create()
        sector_vocabulary = SectorVocabularyFactory.create()

        data = {
            "activity": activity.id,
            "sector": {
                "code": sector.code,
                "name": 'irrelevant',
            },
            "vocabulary": {
                "code": sector_vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://twitter.com/",
            "percentage": 100,
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/sectors/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ActivitySector.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.sector.code, str(data['sector']['code']))
        self.assertEqual(instance.percentage, data['percentage'])

    @skip('NotImplemented')
    def test_update__sector(self):
        _sector = ActivitySectorFactory.create()
        sector = SectorFactory.create(code=89)

        data = {
            "activity": _sector.activity.id,
            "sector": {
                "code": sector.code,
                "name": 'irrelevant',
            },
            "vocabulary": {
                "code": _sector.vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://twitter.com/",
            "percentage": 100,
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/sectors/{}?format=json".format(
                self.publisher.id, _sector.activity.id, _sector.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ActivitySector.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.sector.code, str(data['sector']['code']))
        self.assertEqual(instance.vocabulary.code,
                         str(data['vocabulary']['code']))

    def test_delete__sector(self):
        _sector = ActivitySectorFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/sectors/{}?format=json".format(
                self.publisher.id, _sector.activity.id, _sector.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ActivitySector.objects.get(pk=_sector.id)


@skip
class LocationSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_location(self):

        activity = ActivityFactory.create()
        location_reach = GeographicLocationReachFactory.create()
        location_id_vocabulary = GeographicVocabularyFactory.create()
        exactness = GeographicExactnessFactory.create()
        location_class = GeographicLocationClassFactory.create()
        feature_designation = LocationTypeFactory.create()

        LocationTypeFactory.create()

        data = {
            "activity": activity.id,
            "ref": "AF-KAN",
            "location_reach": {
                "code": location_reach.code,
                "name": "irrelevant",
            },
            "location_id": {
                "code": "1453782",
                "vocabulary": {
                    "code": location_id_vocabulary.code,
                    "name": "irrelevant"
                },
            },
            "name": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "activity_description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "point": {
                "pos": {
                    "latitude": "31.616944",
                    "longitude": "65.716944",
                },
                "srsName": "https://www.opengis.net/def/crs/EPSG/0/4326",
            },
            "exactness": {
                "code": exactness.code,
                "name": "irrelevant",
            },
            "location_class": {
                "code": location_class.code,
                "name": "irrelevant",
            },
            "feature_designation": {
                "code": feature_designation.code,
                "name": "irrelevant",
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/locations/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Location.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.ref, data['ref'])
        self.assertEqual(instance.location_reach.code,
                         data['location_reach']['code'])
        self.assertEqual(instance.location_id_code,
                         data['location_id']['code'])
        self.assertEqual(
            instance.location_id_vocabulary.code,
            data['location_id']['vocabulary']['code'])
        self.assertEqual(instance.exactness.code, data['exactness']['code'])
        self.assertEqual(instance.location_class.code,
                         data['location_class']['code'])
        self.assertEqual(instance.feature_designation.code,
                         data['feature_designation']['code'])

        self.assertEqual(instance.point_srs_name, data['point']['srsName'])
        self.assertEqual(
            str(instance.point_pos[0]), data['point']['pos']['longitude'])
        self.assertEqual(
            str(instance.point_pos[1]), data['point']['pos']['latitude'])

        # order by creation time ('id')
        name_narratives = instance.name.narratives.all().order_by('id')

        self.assertEqual(
            name_narratives[0].content, data['name']['narratives'][0]['text'])
        self.assertEqual(
            name_narratives[1].content, data['name']['narratives'][1]['text'])

        # order by creation time ('id')
        description_narratives = instance.description.narratives.all()\
            .order_by('id')

        self.assertEqual(
            description_narratives[0].content,
            data['description']['narratives'][0]['text'])
        self.assertEqual(
            description_narratives[1].content,
            data['description']['narratives'][1]['text'])

        # order by creation time ('id')
        activity_description_narratives = instance.activity_description.\
            narratives.all().order_by('id')

        self.assertEqual(
            activity_description_narratives[0].content,
            data['activity_description']['narratives'][0]['text'])
        self.assertEqual(
            activity_description_narratives[1].content,
            data['activity_description']['narratives'][1]['text'])

    def test_update_location(self):
        location = LocationFactory.create()

        location_reach = GeographicLocationReachFactory.create(
            code='123')
        location_id_vocabulary = GeographicVocabularyFactory.create(
            code='A4')
        exactness = GeographicExactnessFactory.create(code=2)
        location_class = GeographicLocationClassFactory.create(
            code=2)
        feature_designation = LocationTypeFactory.create(
            code='PPLQ')

        LocationTypeFactory.create()

        data = {
            "activity": location.activity.id,
            "ref": "AF-KAN",
            "location_reach": {
                "code": location_reach.code,
                "name": "irrelevant",
            },
            "location_id": {
                "code": "1453782",
                "vocabulary": {
                    "code": location_id_vocabulary.code,
                    "name": "irrelevant"
                },
            },
            "name": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "activity_description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
            "point": {
                "pos": {
                    "latitude": "31.616944",
                    "longitude": "65.716944",
                },
                "srsName": "https://www.opengis.net/def/crs/EPSG/0/4326",
            },
            "exactness": {
                "code": exactness.code,
                "name": "irrelevant",
            },
            "location_class": {
                "code": location_class.code,
                "name": "irrelevant",
            },
            "feature_designation": {
                "code": feature_designation.code,
                "name": "irrelevant",
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/locations/{}?format=json".format(
                self.publisher.id, location.activity.id, location.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Location.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.ref, data['ref'])
        self.assertEqual(instance.location_reach.code,
                         data['location_reach']['code'])
        self.assertEqual(instance.location_id_code,
                         data['location_id']['code'])
        self.assertEqual(
            instance.location_id_vocabulary.code,
            data['location_id']['vocabulary']['code'])
        self.assertEqual(instance.exactness.code,
                         str(data['exactness']['code']))
        self.assertEqual(instance.location_class.code,
                         data['location_class']['code'])
        self.assertEqual(instance.feature_designation.code,
                         data['feature_designation']['code'])

        self.assertEqual(instance.point_srs_name, data['point']['srsName'])
        self.assertEqual(
            str(instance.point_pos[0]), data['point']['pos']['longitude'])
        self.assertEqual(
            str(instance.point_pos[1]), data['point']['pos']['latitude'])

        # order by creation time ('id')
        name_narratives = instance.name.narratives.all().order_by('id')

        self.assertEqual(
            name_narratives[0].content, data['name']['narratives'][0]['text'])
        self.assertEqual(
            name_narratives[1].content, data['name']['narratives'][1]['text'])

        # order by creation time ('id')
        description_narratives = instance.description.narratives.all()\
            .order_by('id')

        self.assertEqual(
            description_narratives[0].content,
            data['description']['narratives'][0]['text'])
        self.assertEqual(
            description_narratives[1].content,
            data['description']['narratives'][1]['text'])

        # order by creation time ('id')
        activity_description_narratives = instance.activity_description.\
            narratives.all().order_by('id')

        self.assertEqual(
            activity_description_narratives[0].content,
            data['activity_description']['narratives'][0]['text'])
        self.assertEqual(
            activity_description_narratives[1].content,
            data['activity_description']['narratives'][1]['text'])

    def test_delete_location(self):
        location = LocationFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/locations/{}?format=json".format(
                self.publisher.id, location.activity.id, location.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Location.objects.get(pk=location.id)


@skip
class HumanitarianScopeSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_humanitarian_scope(self):

        activity = ActivityFactory.create()
        type = HumanitarianScopeTypeFactory.create()
        vocabulary = HumanitarianScopeVocabularyFactory.create()

        data = {
            "activity": activity.id,
            "code": "1",
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "vocabulary": {
                "code": vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://github.com/zimmerman-team",
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/humanitarian_scopes/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.HumanitarianScope.objects.get(pk=res.json()[
                                                             'id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])
        self.assertEqual(instance.vocabulary.code, data['vocabulary']['code'])
        self.assertEqual(instance.vocabulary_uri, data['vocabulary_uri'])

    def test_update_humanitarian_scope(self):
        humanitarian_scope = HumanitarianScopeFactory.create()
        type = HumanitarianScopeTypeFactory.create(code="2")
        vocabulary = HumanitarianScopeVocabularyFactory.create(
            code="2")

        data = {
            "activity": humanitarian_scope.activity.id,
            "code": "1",
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "vocabulary": {
                "code": vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://github.com/zimmerman-team",
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/humanitarian_scopes/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                humanitarian_scope.activity.id,
                humanitarian_scope.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.HumanitarianScope.objects.get(pk=res.json()[
                                                             'id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])
        self.assertEqual(instance.vocabulary.code, data['vocabulary']['code'])
        self.assertEqual(instance.vocabulary_uri, data['vocabulary_uri'])

    def test_delete_humanitarian_scope(self):
        humanitarian_scopes = HumanitarianScopeFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/humanitarian_scopes/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                humanitarian_scopes.activity.id,
                humanitarian_scopes.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.HumanitarianScope.objects.get(
                pk=humanitarian_scopes.id)


@skip
class PolicyMarkerSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_policy_marker(self):
        activity = ActivityFactory.create()
        vocabulary = PolicyMarkerVocabularyFactory.create()
        significance = PolicySignificanceFactory.create()
        policy_marker = PolicyMarkerFactory.create()

        data = {
            "activity": activity.id,
            "vocabulary": {
                "code": vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://twitter.com/",
            "policy_marker": {
                "code": policy_marker.code,
                "name": 'irrelevant',
            },
            "significance": {
                "code": significance.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/policy_markers/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ActivityPolicyMarker.objects.get(pk=res.json()[
                                                                'id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.vocabulary.code, data['vocabulary']['code'])
        self.assertEqual(instance.vocabulary_uri, data['vocabulary_uri'])
        self.assertEqual(instance.code.code, str(
            data['policy_marker']['code']))
        self.assertEqual(instance.significance.code,
                         str(data['significance']['code']))

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_update_policy_marker(self):
        activity_policy_marker = ActivityPolicyMarkerFactory.create()
        vocabulary = PolicyMarkerVocabularyFactory.create(code=2)
        policy_marker = PolicyMarkerFactory.create(code=2)
        significance = PolicySignificanceFactory.create(code=2)

        data = {
            "activity": activity_policy_marker.activity.id,
            "vocabulary": {
                "code": vocabulary.code,
                "name": 'irrelevant',
            },
            "vocabulary_uri": "https://twitter.com/",
            "policy_marker": {
                "code": policy_marker.code,
                "name": 'irrelevant',
            },
            "significance": {
                "code": significance.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/policy_markers/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                activity_policy_marker.activity.id,
                activity_policy_marker.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ActivityPolicyMarker.objects.get(pk=res.json()[
                                                                'id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.vocabulary.code,
                         str(data['vocabulary']['code']))
        self.assertEqual(instance.vocabulary_uri, data['vocabulary_uri'])
        self.assertEqual(instance.code.code, str(
            data['policy_marker']['code']))
        self.assertEqual(instance.significance.code,
                         str(data['significance']['code']))

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_delete_policy_marker(self):
        participating_org = ActivityPolicyMarkerFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/policy_markers/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                participating_org.activity.id,
                participating_org.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ActivityPolicyMarker.objects.get(
                pk=participating_org.id)


@skip
class BudgetSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_budget(self):

        activity = ActivityFactory.create()
        type = BudgetTypeFactory.create()
        status = BudgetStatusFactory.create()
        currency = CurrencyFactory.create()

        data = {
            "activity": activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "status": {
                "code": status.code,
                "name": 'irrelevant',
            },
            "period_start": datetime.date.today().isoformat(),
            "period_end": datetime.date.today().isoformat(),
            "value": {
                "value": 123456,
                "currency": {
                    "code": currency.code,
                    "name": 'irrelevant',
                },
                "date": datetime.date.today().isoformat(),
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/budgets/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Budget.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])
        self.assertEqual(instance.status.code, data['status']['code'])
        self.assertEqual(instance.period_start.isoformat(),
                         data['period_start'])
        self.assertEqual(instance.period_end.isoformat(), data['period_end'])
        self.assertEqual(instance.value, data['value']['value'])
        self.assertEqual(instance.currency.code,
                         data['value']['currency']['code'])
        self.assertEqual(instance.value_date.isoformat(),
                         data['value']['date'])

    def test_update_budget(self):
        budget = BudgetFactory.create()
        type = BudgetTypeFactory.create(code="2")
        status = BudgetStatusFactory.create(code="2")
        currency = CurrencyFactory.create(code='af')

        data = {
            "activity": budget.activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "status": {
                "code": status.code,
                "name": 'irrelevant',
            },
            "period_start": datetime.date.today().isoformat(),
            "period_end": datetime.date.today().isoformat(),
            "value": {
                "value": 123456,
                "currency": {
                    "code": currency.code,
                    "name": 'irrelevant',
                },
                "date": datetime.date.today().isoformat(),
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/budgets/{}?format=json".format(
                self.publisher.id, budget.activity.id, budget.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Budget.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])
        self.assertEqual(instance.status.code, data['status']['code'])
        self.assertEqual(instance.period_start.isoformat(),
                         data['period_start'])
        self.assertEqual(instance.period_end.isoformat(), data['period_end'])
        self.assertEqual(instance.value, data['value']['value'])
        self.assertEqual(instance.currency.code,
                         data['value']['currency']['code'])
        self.assertEqual(instance.value_date.isoformat(),
                         data['value']['date'])

    def test_delete_budget(self):
        budgets = BudgetFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/budgets/{}?format=json".format(
                self.publisher.id, budgets.activity.id, budgets.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Budget.objects.get(pk=budgets.id)


@skip
class PlannedDisbursementSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_planned_disbursement(self):

        activity = ActivityFactory.create()
        type = BudgetTypeFactory.create()
        currency = CurrencyFactory.create()
        organisation = OrganisationFactory.create()
        organisation_type = OrganisationTypeFactory.create(code=9)
        activity2 = ActivityFactory.create(
            iati_identifier="IATI-0002")

        data = {
            "activity": activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "period_start": datetime.date.today().isoformat(),
            "period_end": datetime.date.today().isoformat(),
            "value": {
                "value": 123456,
                "currency": {
                    "code": currency.code,
                    "name": 'irrelevant',
                },
                "date": datetime.date.today().isoformat(),
            },
            "provider_organisation": {
                "ref": organisation.organisation_identifier,
                "type": {
                    "code": organisation_type.code,
                    "name": 'irrelevant',
                },
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "receiver_organisation": {
                "ref": organisation.organisation_identifier,
                "type": {
                    "code": organisation_type.code,
                    "name": 'irrelevant',
                },
                "receiver_activity": activity2.id,
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/planned_disbursements/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.PlannedDisbursement.objects.get(pk=res.json()[
                                                               'id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])
        self.assertEqual(instance.period_start.isoformat(),
                         data['period_start'])
        self.assertEqual(instance.period_end.isoformat(), data['period_end'])
        self.assertEqual(instance.value, data['value']['value'])
        self.assertEqual(instance.currency.code,
                         data['value']['currency']['code'])
        self.assertEqual(instance.value_date.isoformat(),
                         data['value']['date'])

        instance2 = iati_models.PlannedDisbursementProvider.objects.get(
            planned_disbursement_id=res.json()['id'])
        self.assertEqual(instance2.ref, data['provider_organisation']['ref'])
        self.assertEqual(instance2.normalized_ref,
                         data['provider_organisation']['ref'])
        self.assertEqual(
            instance2.organisation.organisation_identifier,
            data['provider_organisation']['ref'])
        self.assertEqual(instance2.type.code, str(
            data['provider_organisation']['type']['code']))
        self.assertEqual(instance2.provider_activity.id, activity.id)

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(
            narratives2[0].content,
            data['provider_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives2[1].content,
            data['provider_organisation']['narratives'][1]['text']
        )

        instance3 = iati_models.PlannedDisbursementReceiver.objects.get(
            planned_disbursement_id=res.json()['id'])
        self.assertEqual(instance3.ref, data['receiver_organisation']['ref'])
        self.assertEqual(instance3.normalized_ref,
                         data['receiver_organisation']['ref'])
        self.assertEqual(
            instance3.organisation.organisation_identifier,
            data['receiver_organisation']['ref'])
        self.assertEqual(instance3.type.code, str(
            data['receiver_organisation']['type']['code']))
        self.assertEqual(instance3.receiver_activity.id,
                         data['receiver_organisation']['receiver_activity'])

        # order by creation time ('id')
        narratives3 = instance3.narratives.all().order_by('id')

        self.assertEqual(
            narratives3[0].content,
            data['receiver_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives3[1].content,
            data['receiver_organisation']['narratives'][1]['text']
        )

    def test_update_planned_disbursement(self):
        planned_disbursement = PlannedDisbursementFactory.create()
        type = BudgetTypeFactory.create()
        currency = CurrencyFactory.create()
        organisation = OrganisationFactory.create()
        organisation_type = OrganisationTypeFactory.create(code=9)
        activity2 = ActivityFactory.create(
            iati_identifier="IATI-0002")

        data = {
            "activity": planned_disbursement.activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "period_start": datetime.date.today().isoformat(),
            "period_end": datetime.date.today().isoformat(),
            "value": {
                "value": 123456,
                "currency": {
                    "code": currency.code,
                    "name": 'irrelevant',
                },
                "date": datetime.date.today().isoformat(),
            },
            "provider_organisation": {
                "ref": organisation.organisation_identifier,
                "type": {
                    "code": organisation_type.code,
                    "name": 'irrelevant',
                },
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "receiver_organisation": {
                "ref": organisation.organisation_identifier,
                "type": {
                    "code": organisation_type.code,
                    "name": 'irrelevant',
                },
                "receiver_activity": activity2.id,
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/planned_disbursements/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                planned_disbursement.activity.id,
                planned_disbursement.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.PlannedDisbursement.objects.get(pk=res.json()[
                                                               'id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])
        self.assertEqual(instance.period_start.isoformat(),
                         data['period_start'])
        self.assertEqual(instance.period_end.isoformat(), data['period_end'])
        self.assertEqual(instance.value, data['value']['value'])
        self.assertEqual(instance.currency.code,
                         data['value']['currency']['code'])
        self.assertEqual(instance.value_date.isoformat(),
                         data['value']['date'])

        instance2 = iati_models.PlannedDisbursementProvider.objects.get(
            planned_disbursement_id=res.json()['id'])
        self.assertEqual(instance2.ref, data['provider_organisation']['ref'])
        self.assertEqual(instance2.normalized_ref,
                         data['provider_organisation']['ref'])
        self.assertEqual(
            instance2.organisation.organisation_identifier,
            data['provider_organisation']['ref'])
        self.assertEqual(instance2.type.code, str(
            data['provider_organisation']['type']['code']))
        self.assertEqual(instance2.provider_activity.id,
                         planned_disbursement.activity.id)

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(
            narratives2[0].content,
            data['provider_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives2[1].content,
            data['provider_organisation']['narratives'][1]['text']
        )

        instance3 = iati_models.PlannedDisbursementReceiver.objects.get(
            planned_disbursement_id=res.json()['id'])
        self.assertEqual(instance3.ref, data['receiver_organisation']['ref'])
        self.assertEqual(instance3.normalized_ref,
                         data['receiver_organisation']['ref'])
        self.assertEqual(
            instance3.organisation.organisation_identifier,
            data['receiver_organisation']['ref'])
        self.assertEqual(instance3.type.code, str(
            data['receiver_organisation']['type']['code']))
        self.assertEqual(instance3.receiver_activity.id,
                         data['receiver_organisation']['receiver_activity'])

        # order by creation time ('id')
        narratives3 = instance3.narratives.all().order_by('id')

        self.assertEqual(
            narratives3[0].content,
            data['receiver_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives3[1].content,
            data['receiver_organisation']['narratives'][1]['text']
        )

    def test_delete_planned_disbursement(self):
        planned_disbursements = PlannedDisbursementFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/planned_disbursements/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                planned_disbursements.activity.id,
                planned_disbursements.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.PlannedDisbursement.objects.get(
                pk=planned_disbursements.id)


@skip
class TransactionSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_transaction(self):
        activity = ActivityFactory.create()
        transaction_type = transaction_factory.TransactionTypeFactory.create()
        currency = CurrencyFactory.create()
        organisation_type = OrganisationTypeFactory.create()
        organisation = OrganisationFactory.create()
        activity2 = ActivityFactory.create(
            iati_identifier="IATI-0002")
        sector = SectorFactory.create()
        sector_vocabulary = SectorVocabularyFactory.create()
        country = CountryFactory.create()
        region = RegionFactory.create()
        region_vocabulary = RegionVocabularyFactory.create()
        disbursement_channel = codelist_factory.DisbursementChannelFactory\
            .create()
        flow_type = FlowTypeFactory.create()
        finance_type = FinanceTypeFactory.create()
        aid_type = AidTypeFactory.create()
        tied_status = TiedStatusFactory.create()

        data = {
            "activity_id": activity.id,
            "ref": "test-ref",
            "humanitarian": 1,
            "transaction_date": datetime.date.today().isoformat(),
            "value": 123456,
            "value_date": datetime.date.today().isoformat(),
            "currency": {
                "code": currency.code,
                "name": 'irrelevant',
            },
            "date": datetime.date.today().isoformat(),
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "provider_organisation": {
                "ref": organisation.organisation_identifier,
                "type": {
                    "code": organisation_type.code,
                    "name": 'irrelevant',
                },
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "receiver_organisation": {
                "ref": organisation.organisation_identifier,
                "type": {
                    "code": organisation_type.code,
                    "name": 'irrelevant',
                },
                "receiver_activity_id": activity2.iati_identifier,
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "disbursement_channel": {
                "code": disbursement_channel.code,
                "name": 'irrelevant',
            },
            "transaction_type": {
                "code": transaction_type.code,
                "name": 'irrelevant',
            },
            "recipient_country": {
                "country": {
                    "code": country.code,
                    "name": 'irrelevant',
                }
            },
            "recipient_region": {
                "region": {
                    "code": region.code,
                    "name": 'irrelevant',
                },
                "vocabulary": {
                    "code": region_vocabulary.code,
                    "name": 'irrelevant',
                },
                "vocabulary_uri": "https://twitter.com/",
            },
            "sector": {
                "sector": {
                    "code": sector.code,
                    "name": 'irrelevant',
                },
                "vocabulary": {
                    "code": sector_vocabulary.code,
                    "name": 'irrelevant',
                },
                "vocabulary_uri": "https://twitter.com/",
            },
            "flow_type": {
                "code": flow_type.code,
                "name": 'irrelevant',
            },
            "finance_type": {
                "code": finance_type.code,
                "name": 'irrelevant',
            },
            "aid_type": {
                "code": aid_type.code,
                "name": 'irrelevant',
            },
            "tied_status": {
                "code": tied_status.code,
                "name": 'irrelevant',
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/transactions/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        result = res.json()

        self.assertEqual(res.status_code, 201, result)

        instance = transaction_models.Transaction.objects.get(pk=result['id'])

        self.assertEqual(instance.activity.id, data['activity_id'])
        self.assertEqual(instance.finance_type.code,
                         data['finance_type']['code'])
        self.assertEqual(instance.transaction_date.isoformat(),
                         data['transaction_date'])
        self.assertEqual(instance.value, data['value'])
        self.assertEqual(instance.currency.code, data['currency']['code'])
        self.assertEqual(instance.value_date.isoformat(), data['date'])
        self.assertEqual(instance.flow_type.code,
                         str(data['flow_type']['code']))
        self.assertEqual(instance.finance_type.code,
                         str(data['finance_type']['code']))
        self.assertEqual(instance.aid_type.code, str(data['aid_type']['code']))
        self.assertEqual(instance.tied_status.code,
                         str(data['tied_status']['code']))
        self.assertEqual(instance.disbursement_channel.code,
                         data['disbursement_channel']['code'])
        self.assertEqual(instance.humanitarian, data['humanitarian'])
        self.assertEqual(
            instance.transactionrecipientcountry_set.all()[0].country.code,
            data['recipient_country']['country']['code']
        )
        self.assertEqual(
            instance.transactionrecipientcountry_set.all()
            [0].reported_transaction.pk, instance.pk
        )
        self.assertEqual(
            instance.transactionrecipientregion_set.all()[0].region.code,
            data['recipient_region']['region']['code']
        )
        self.assertEqual(instance.transactionrecipientregion_set.all()
                         [0].reported_transaction.pk, instance.pk)
        self.assertEqual(
            instance.transactionsector_set.all()[0].sector.code,
            data['sector']['sector']['code'])
        self.assertEqual(instance.transactionsector_set.all()[
                         0].reported_transaction.pk, instance.pk)

        instance2 = transaction_models.TransactionProvider.objects.get(
            transaction_id=result['id'])
        self.assertEqual(instance2.ref, data['provider_organisation']['ref'])
        self.assertEqual(instance2.normalized_ref,
                         data['provider_organisation']['ref'])
        self.assertEqual(
            instance2.organisation.organisation_identifier,
            data['provider_organisation']['ref'])
        self.assertEqual(instance2.type.code, str(
            data['provider_organisation']['type']['code']))
        self.assertEqual(instance2.provider_activity.id, activity.id)

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(
            narratives2[0].content,
            data['provider_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives2[1].content,
            data['provider_organisation']['narratives'][1]['text']
        )

        instance3 = transaction_models.TransactionReceiver.objects.get(
            transaction_id=result['id'])
        self.assertEqual(instance3.ref, data['receiver_organisation']['ref'])
        self.assertEqual(instance3.normalized_ref,
                         data['receiver_organisation']['ref'])
        self.assertEqual(
            instance3.organisation.organisation_identifier,
            data['receiver_organisation']['ref'])
        self.assertEqual(instance3.type.code, str(
            data['receiver_organisation']['type']['code']))
        self.assertEqual(
            instance3.receiver_activity.iati_identifier,
            data['receiver_organisation']['receiver_activity_id'])

        # order by creation time ('id')
        narratives3 = instance3.narratives.all().order_by('id')

        self.assertEqual(
            narratives3[0].content,
            data['receiver_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives3[1].content,
            data['receiver_organisation']['narratives'][1]['text']
        )

    def test_update_transaction(self):
        transaction = transaction_factory.TransactionFactory.create()
        transaction_provider = transaction_factory.TransactionProviderFactory.\
            create(transaction=transaction)
        transaction_receiver = transaction_factory.TransactionReceiverFactory.\
            create(transaction=transaction)
        transaction_recipient_country = transaction_factory.\
            TransactionRecipientCountryFactory(
                transaction=transaction,
                reported_transaction=transaction
            )
        transaction_recipient_region = transaction_factory\
            .TransactionRecipientRegionFactory.create(
                transaction=transaction,
                reported_transaction=transaction
            )
        transaction_sector = transaction_factory\
            .TransactionSectorFactory.create(
                transaction=transaction,
                reported_transaction=transaction
            )
        transaction_type = transaction_factory.TransactionTypeFactory.create(
            code="2")
        currency = CurrencyFactory.create(code="af")
        OrganisationTypeFactory.create()
        OrganisationFactory.create()
        ActivityFactory.create(
            iati_identifier="IATI-0002")
        SectorFactory.create()
        SectorVocabularyFactory.create()
        CountryFactory.create()
        RegionFactory.create()
        RegionVocabularyFactory.create()
        disbursement_channel = codelist_factory.DisbursementChannelFactory\
            .create()
        flow_type = FlowTypeFactory.create()
        finance_type = FinanceTypeFactory.create()
        aid_type = AidTypeFactory.create()
        tied_status = TiedStatusFactory.create()

        data = {
            "activity_id": transaction.activity.id,
            "ref": "test-ref",
            "humanitarian": 1,
            "transaction_date": datetime.date.today().isoformat(),
            "value": 123456,
            "value_date": datetime.date.today().isoformat(),
            "currency": {
                "code": currency.code,
                "name": 'irrelevant',
            },
            "date": datetime.date.today().isoformat(),
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "provider_organisation": {
                "ref": transaction_provider.ref,
                "type": {
                    "code": transaction_provider.type.code,
                    "name": 'irrelevant',
                },
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "receiver_organisation": {
                "ref": transaction_receiver.ref,
                "type": {
                    "code": transaction_receiver.type.code,
                    "name": 'irrelevant',
                },
                "receiver_activity_id": transaction_receiver
                .receiver_activity.id,
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "disbursement_channel": {
                "code": disbursement_channel.code,
                "name": 'irrelevant',
            },
            "transaction_type": {
                "code": transaction_type.code,
                "name": 'irrelevant',
            },
            "recipient_country": {
                "country": {
                    "code": transaction_recipient_country.country.code,
                    "name": 'irrelevant',
                }
            },
            "recipient_region": {
                "region": {
                    "code": transaction_recipient_region.region.code,
                    "name": 'irrelevant',
                },
                "vocabulary": {
                    "code": transaction_recipient_region.vocabulary.code,
                    "name": 'irrelevant',
                },
                "vocabulary_uri": "https://twitter.com/",
            },
            "sector": {
                "sector": {
                    "code": transaction_sector.sector.code,
                    "name": 'irrelevant',
                },
                "vocabulary": {
                    "code": transaction_sector.vocabulary.code,
                    "name": 'irrelevant',
                },
                "vocabulary_uri": "https://twitter.com/",
            },
            "flow_type": {
                "code": flow_type.code,
                "name": 'irrelevant',
            },
            "finance_type": {
                "code": finance_type.code,
                "name": 'irrelevant',
            },
            "aid_type": {
                "code": aid_type.code,
                "name": 'irrelevant',
            },
            "tied_status": {
                "code": tied_status.code,
                "name": 'irrelevant',
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/transactions/{}?format=json".format(  # NOQA: E501
                self.publisher.id, transaction.activity.id, transaction.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())
        result = res.json()

        instance = transaction_models.Transaction.objects.get(pk=result['id'])

        self.assertEqual(instance.activity.id, data['activity_id'])
        self.assertEqual(instance.finance_type.code,
                         data['finance_type']['code'])
        self.assertEqual(instance.transaction_date.isoformat(),
                         data['transaction_date'])
        self.assertEqual(instance.value, data['value'])
        self.assertEqual(instance.currency.code, data['currency']['code'])
        self.assertEqual(instance.value_date.isoformat(), data['date'])
        self.assertEqual(instance.flow_type.code,
                         str(data['flow_type']['code']))
        self.assertEqual(instance.finance_type.code,
                         str(data['finance_type']['code']))
        self.assertEqual(instance.aid_type.code, str(data['aid_type']['code']))
        self.assertEqual(instance.tied_status.code,
                         str(data['tied_status']['code']))
        self.assertEqual(instance.transaction_type.code,
                         data['transaction_type']['code'])
        self.assertEqual(instance.disbursement_channel.code,
                         data['disbursement_channel']['code'])
        self.assertEqual(instance.humanitarian, data['humanitarian'])
        self.assertEqual(
            instance.transactionrecipientcountry_set.all()[0].country.code,
            data['recipient_country']['country']['code']
        )
        self.assertEqual(
            instance
            .transactionrecipientcountry_set.all()[0]
            .reported_transaction.pk,
            instance.pk
        )
        self.assertEqual(
            instance.transactionrecipientregion_set.all()[0].region.code,
            data['recipient_region']['region']['code']
        )
        self.assertEqual(
            instance
            .transactionrecipientregion_set.all()[0]
            .reported_transaction.pk,
            instance.pk
        )
        self.assertEqual(
            instance.transactionsector_set.all()[0].sector.code,
            data['sector']['sector']['code'])
        self.assertEqual(instance.transactionsector_set.all()[
                         0].reported_transaction.pk, instance.pk)

        instance2 = transaction_models.TransactionProvider.objects.get(
            transaction_id=result['id'])
        self.assertEqual(instance2.ref, data['provider_organisation']['ref'])
        self.assertEqual(instance2.type.code, str(
            data['provider_organisation']['type']['code']))
        self.assertEqual(instance2.provider_activity.id, instance.activity.id)

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(
            narratives2[0].content,
            data['provider_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives2[1].content,
            data['provider_organisation']['narratives'][1]['text']
        )

        instance3 = transaction_models.TransactionReceiver.objects.get(
            transaction_id=result['id']
        )
        self.assertEqual(instance3.ref, data['receiver_organisation']['ref'])
        self.assertEqual(instance3.type.code, str(
            data['receiver_organisation']['type']['code']))
        self.assertEqual(instance3.receiver_activity.id,
                         data['receiver_organisation']['receiver_activity_id'])

        # order by creation time ('id')
        narratives3 = instance3.narratives.all().order_by('id')

        self.assertEqual(
            narratives3[0].content,
            data['receiver_organisation']['narratives'][0]['text']
        )
        self.assertEqual(
            narratives3[1].content,
            data['receiver_organisation']['narratives'][1]['text']
        )

    def test_delete_transaction(self):
        transaction = transaction_factory.TransactionFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/transactions/{}?format=json".format(  # NOQA: E501
                self.publisher.id, transaction.activity.id, transaction.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            transaction_models.Transaction.objects.get(
                pk=transaction.id)


@skip
class ResultSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_result(self):

        activity = ActivityFactory.create()
        type = ResultTypeFactory.create()

        data = {
            "activity": activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "aggregation_status": 1,
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/results/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Result.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])

        instance2 = iati_models.ResultTitle.objects.get(
            result_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['title']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['title']['narratives'][1]['text'])

        instance2 = iati_models.ResultDescription.objects.get(
            result_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['description']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['description']['narratives'][1]['text'])

    def test_update_result(self):
        result = ResultFactory.create()
        type = ResultTypeFactory.create(code="2")

        data = {
            "activity": result.activity.id,
            "type": {
                "code": type.code,
                "name": 'irrelevant',
            },
            "aggregation_status": 0,
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/results/{}?format=json".format(
                self.publisher.id, result.activity.id, result.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Result.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.type.code, data['type']['code'])

        instance2 = iati_models.ResultTitle.objects.get(
            result_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['title']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['title']['narratives'][1]['text'])

        instance2 = iati_models.ResultDescription.objects.get(
            result_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['description']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['description']['narratives'][1]['text'])

    def test_delete_result(self):
        results = ResultFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/results/{}?format=json".format(
                self.publisher.id, results.activity.id, results.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Result.objects.get(pk=results.id)


@skip
class ResultIndicatorSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_result_indicator(self):

        result = ResultFactory.create()
        measure = IndicatorMeasureFactory.create()

        data = {
            "result": result.id,
            "measure": {
                "code": measure.code,
                "name": 'irrelevant',
            },
            "ascending": 1,
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "baseline": {
                "year": 2012,
                "value": "10",
                "comment": {
                    "narratives": [
                        {
                            "text": "test1"
                        },
                        {
                            "text": "test2"
                        }
                    ],
                }
            }
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/results/{}/indicators/?format=json".format(  # NOQA: E501
                self.publisher.id, result.activity.id, result.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ResultIndicator.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.result.id, data['result'])
        self.assertEqual(instance.measure.code, data['measure']['code'])
        self.assertEqual(instance.ascending, data['ascending'])

        instance2 = iati_models.ResultIndicatorTitle.objects.get(
            result_indicator_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['title']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['title']['narratives'][1]['text'])

        instance2 = iati_models.ResultIndicatorDescription.objects.get(
            result_indicator_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['description']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['description']['narratives'][1]['text'])

    def test_update_result_indicator(self):
        result_indicator = ResultIndicatorFactory.create()
        measure = IndicatorMeasureFactory.create(code="2")

        data = {
            "result": result_indicator.result.id,
            "measure": {
                "code": measure.code,
                "name": 'irrelevant',
            },
            "ascending": 1,
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "baseline": {
                "year": 2012,
                "value": "10",
                "comment": {
                    "narratives": [
                        {
                            "text": "test1"
                        },
                        {
                            "text": "test2"
                        }
                    ],
                }
            }
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/results/{}/indicators/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                result_indicator.result.activity.id,
                result_indicator.result.id,
                result_indicator.id),
            data,
            format='json')

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.ResultIndicator.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.result.id, data['result'])
        self.assertEqual(instance.measure.code, data['measure']['code'])
        self.assertEqual(instance.ascending, data['ascending'])

        instance2 = iati_models.ResultIndicatorTitle.objects.get(
            result_indicator_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['title']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['title']['narratives'][1]['text'])

        instance2 = iati_models.ResultIndicatorDescription.objects.get(
            result_indicator_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['description']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['description']['narratives'][1]['text'])

    def test_delete_result_indicator(self):
        result_indicator = ResultIndicatorFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/results/{}/indicators/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                result_indicator.result.activity.id,
                result_indicator.result.id,
                result_indicator.id),
            format='json')

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ResultIndicator.objects.get(
                pk=result_indicator.id)


@skip
class ResultIndicatorReferenceSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_result_indicator_reference(self):
        result_indicator = ResultIndicatorFactory.create()
        indicator_vocabulary = vocabulary_factory\
            .IndicatorVocabularyFactory.create()

        data = {
            "result_indicator": result_indicator.id,
            "vocabulary": {
                "code": indicator_vocabulary.code,
                "name": 'irrelevant',
            },
            "code": "1",
            "indicator_uri": "https://twitter.com/",
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/results/{}/indicators/{}/references/?format=json".format(  # NOQA: E501
                self.publisher.id,
                result_indicator.result.activity.id,
                result_indicator.result.id,
                result_indicator.id),
            data,
            format='json')

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ResultIndicatorReference.objects.get(
            pk=res.json()['id']
        )

        self.assertEqual(instance.result_indicator.id,
                         data['result_indicator'])
        self.assertEqual(instance.code, data['code'])
        self.assertEqual(instance.vocabulary.code, data['vocabulary']['code'])
        self.assertEqual(instance.indicator_uri, data['indicator_uri'])

    def test_update_result_indicator_reference(self):
        result_indicator_reference = ResultIndicatorReferenceFactory.create()
        indicator_vocabulary = vocabulary_factory\
            .IndicatorVocabularyFactory.create(
                code="2"
            )

        data = {
            "result_indicator": result_indicator_reference.result_indicator.id,
            "vocabulary": {
                "code": indicator_vocabulary.code,
                "name": 'irrelevant',
            },
            "code": "2",
            "indicator_uri": "https://twitter.com/",
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/results/{}/indicators/{}/references/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                result_indicator_reference.result_indicator.result.activity.id,
                result_indicator_reference.result_indicator.result.id,
                result_indicator_reference.result_indicator.id,
                result_indicator_reference.id),
            data,
            format='json')

        self.assertEqual(res.status_code, 200, res.json())

    def test_delete_result_indicator_reference(self):
        result_indicator_reference = ResultIndicatorReferenceFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/results/{}/indicators/{}/references/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                result_indicator_reference.result_indicator.result.activity.id,
                result_indicator_reference.result_indicator.result.id,
                result_indicator_reference.result_indicator.id,
                result_indicator_reference.id),
            format='json')

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.ResultIndicatorReference.objects.get(
                pk=result_indicator_reference.id)


@skip
class ResultIndicatorPeriodTargetLocationSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_result_indicator_period_target_location(self):
        result_indicator_period_target = ResultIndicatorPeriodTargetFactory.create()  # NOQA: E501
        result_indicator_period = result_indicator_period_target\
            .result_indicator_period

        location = LocationFactory.create(
            activity=result_indicator_period.result_indicator.result.activity)

        data = {
            "result_indicator_period": result_indicator_period.id,
            "result_indicator_period_target": result_indicator_period_target.id,  # NOQA: E501
            "ref": location.ref,
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/results/{}/indicators/{}/periods/{}/target/{}/location/?format=json".format(  # NOQA: E501
                self.publisher.id,
                result_indicator_period.result_indicator.result.activity.id,
                result_indicator_period.result_indicator.result.id,
                result_indicator_period.result_indicator.id,
                result_indicator_period.id,
                result_indicator_period_target.id
            ),
            data,
            format='json')

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.ResultIndicatorPeriodTargetLocation.objects.get(
            pk=res.json()['id'])

        self.assertEqual(
            instance.result_indicator_period_target.result_indicator_period.id,
            data['result_indicator_period']
        )
        self.assertEqual(instance.ref, data['ref'])
        self.assertEqual(instance.location.ref, data['ref'])


@skip
class OtherIdentifierSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_other_identifier(self):
        activity = ActivityFactory.create()
        other_identifier_type = codelist_factory\
            .OtherIdentifierTypeFactory.create()

        data = {
            "activity": activity.id,
            "ref": "some-ref",
            "type": {
                "code": other_identifier_type.code,
                "name": 'irrelevant',
            },
            "owner_org": {
                "ref": "org-id",
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            }
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/other_identifiers/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.OtherIdentifier.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.identifier, data['ref'])
        self.assertEqual(instance.type.code, str(data['type']['code']))
        self.assertEqual(instance.owner_ref, data['owner_org']['ref'])

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content,
                         data['owner_org']['narratives'][0]['text'])
        self.assertEqual(narratives[1].content,
                         data['owner_org']['narratives'][1]['text'])

    def test_update_other_identifier(self):
        other_identifier = OtherIdentifierFactory.create()
        other_identifier_type = codelist_factory.OtherIdentifierTypeFactory\
            .create(code="A10")

        data = {
            "activity": other_identifier.activity.id,
            "ref": "some-other-ref",
            "type": {
                "code": other_identifier_type.code,
                "name": 'irrelevant',
            },
            "owner_org": {
                "ref": "org-id",
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            }
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/other_identifiers/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                other_identifier.activity.id,
                other_identifier.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.OtherIdentifier.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.identifier, data['ref'])
        self.assertEqual(instance.type.code, str(data['type']['code']))
        self.assertEqual(instance.owner_ref, data['owner_org']['ref'])

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content,
                         data['owner_org']['narratives'][0]['text'])
        self.assertEqual(narratives[1].content,
                         data['owner_org']['narratives'][1]['text'])

    def test_delete_other_identifier(self):
        other_identifier = OtherIdentifierFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/other_identifiers/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                other_identifier.activity.id,
                other_identifier.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.OtherIdentifier.objects.get(
                pk=other_identifier.id)


@skip
class CountryBudgetItemsSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_country_budget_items(self):
        activity = ActivityFactory.create()
        vocabulary = vocabulary_factory.BudgetIdentifierVocabularyFactory\
            .create()

        data = {
            "activity": activity.id,
            "ref": "some-ref",
            "vocabulary": {
                "code": vocabulary.code,
                "name": 'irrelevant',
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/country_budget_items/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.CountryBudgetItem.objects.get(pk=res.json()[
                                                             'id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.vocabulary.code, data['vocabulary']['code'])

    def test_update_country_budget_items(self):
        country_budget_items = CountryBudgetItemFactory.create()
        vocabulary = vocabulary_factory.BudgetIdentifierVocabularyFactory\
            .create(code="A0")

        data = {
            "activity": country_budget_items.activity.id,
            "ref": "some-ref",
            "vocabulary": {
                "code": vocabulary.code,
                "name": 'irrelevant',
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/country_budget_items/?format=json".format(  # NOQA: E501
                self.publisher.id, country_budget_items.activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.CountryBudgetItem.objects.get(pk=res.json()[
                                                             'id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.vocabulary.code, data['vocabulary']['code'])

    def test_delete_country_budget_items(self):
        country_budget_items = CountryBudgetItemFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/country_budget_items/?format=json".format(  # NOQA: E501
                self.publisher.id, country_budget_items.activity.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.CountryBudgetItem.objects.get(
                pk=country_budget_items.id)


@skip
class BudgetItemSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_budget_item(self):
        country_budget_item = CountryBudgetItemFactory.create()
        budget_identifier = codelist_factory.BudgetIdentifierFactory.create()

        data = {
            "country_budget_item": country_budget_item.id,
            "budget_identifier": {
                "code": budget_identifier.code,
                "name": 'irrelevant',
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/country_budget_items/budget_items/?format=json".format(  # NOQA: E501
                self.publisher.id,
                country_budget_item.activity.id),
            data,
            format='json')

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.BudgetItem.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.country_budget_item.id,
                         data['country_budget_item'])
        self.assertEqual(instance.code.code, data['budget_identifier']['code'])

        # order by creation time ('id')
        narratives = instance.description.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content,
                         data['description']['narratives'][0]['text'])
        self.assertEqual(narratives[1].content,
                         data['description']['narratives'][1]['text'])

    def test_update_budget_item(self):
        budget_item = BudgetItemFactory.create()
        budget_identifier = codelist_factory.BudgetIdentifierFactory.create(
            code="1.3.2")

        data = {
            "country_budget_item": budget_item.country_budget_item.id,
            "budget_identifier": {
                "code": budget_identifier.code,
                "name": 'irrelevant',
            },
            "description": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ]
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/country_budget_items/budget_items/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                budget_item.country_budget_item.activity.id,
                budget_item.id),
            data,
            format='json')

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.BudgetItem.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.country_budget_item.id,
                         data['country_budget_item'])
        self.assertEqual(instance.code.code, data['budget_identifier']['code'])

        # order by creation time ('id')
        narratives = instance.description.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content,
                         data['description']['narratives'][0]['text'])
        self.assertEqual(narratives[1].content,
                         data['description']['narratives'][1]['text'])

    def test_delete_budget_item(self):
        budget_item = BudgetItemFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/country_budget_items/budget_items/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                budget_item.country_budget_item.activity.id,
                budget_item.id),
            format='json')

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.BudgetItem.objects.get(pk=budget_item.id)


@skip
class LegacyDataSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_legacy_data(self):
        activity = ActivityFactory.create()

        data = {
            "activity": activity.id,
            "name": "old",
            "value": "old",
            "iati_equivalent": "activity-super-type",
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/legacy_data/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.LegacyData.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.name, data['name'])
        self.assertEqual(instance.value, data['value'])
        self.assertEqual(instance.iati_equivalent, data['iati_equivalent'])

    def test_update_legacy_data(self):
        legacy_data = LegacyDataFactory.create()

        data = {
            "activity": legacy_data.activity.id,
            "name": "old",
            "value": "old",
            "iati_equivalent": "activity-super-type",
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/legacy_data/{}?format=json".format(  # NOQA: E501
                self.publisher.id, legacy_data.activity.id, legacy_data.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.LegacyData.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.name, data['name'])
        self.assertEqual(instance.value, data['value'])
        self.assertEqual(instance.iati_equivalent, data['iati_equivalent'])

    def test_delete_legacy_data(self):
        legacy_data = LegacyDataFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/legacy_data/{}?format=json".format(  # NOQA: E501
                self.publisher.id, legacy_data.activity.id, legacy_data.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.LegacyData.objects.get(pk=legacy_data.id)


@skip
class ConditionsSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_conditions(self):
        activity = ActivityFactory.create()

        data = {
            "activity": activity.id,
            "attached": "1",
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/conditions/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Conditions.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.attached, bool(data['attached']))

    def test_update_conditions(self):
        conditions = ConditionsFactory.create()

        data = {
            "activity": conditions.activity.id,
            "attached": "1",
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/conditions/?format=json".format(
                self.publisher.id, conditions.activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Conditions.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.attached, bool(data['attached']))

    def test_delete_conditions(self):
        conditions = ConditionsFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/conditions/?format=json".format(
                self.publisher.id, conditions.activity.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Conditions.objects.get(pk=conditions.id)


@skip
class ConditionSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_condition(self):
        conditions = ConditionsFactory.create()
        condition_type = codelist_factory.ConditionTypeFactory.create()

        data = {
            "conditions": conditions.id,
            "type": {
                "code": condition_type.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/conditions/condition/?format=json".format(  # NOQA: E501
                self.publisher.id, conditions.activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Condition.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.conditions.id, data['conditions'])
        self.assertEqual(instance.type.code, data['type']['code'])

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_update_condition(self):
        condition = ConditionFactory.create()
        condition_type = codelist_factory.ConditionTypeFactory.create(
            code="1.3.2")

        data = {
            "conditions": condition.conditions.id,
            "type": {
                "code": condition_type.code,
                "name": 'irrelevant',
            },
            "narratives": [
                {
                    "text": "test1"
                },
                {
                    "text": "test2"
                }
            ]
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/conditions/condition/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                condition.conditions.activity.id,
                condition.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Condition.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.conditions.id, data['conditions'])
        self.assertEqual(instance.type.code, data['type']['code'])

        # order by creation time ('id')
        narratives = instance.narratives.all().order_by('id')

        self.assertEqual(narratives[0].content, data['narratives'][0]['text'])
        self.assertEqual(narratives[1].content, data['narratives'][1]['text'])

    def test_delete_condition(self):
        condition = ConditionFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/conditions/condition/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                condition.conditions.activity.id,
                condition.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Condition.objects.get(pk=condition.id)


@skip
class CrsAddSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_crs_add(self):
        activity = ActivityFactory.create()
        repayment_type = LoanRepaymentTypeFactory.create()
        repayment_period = LoanRepaymentPeriodFactory.create()
        currency = CurrencyFactory.create()

        data = {
            "activity": activity.id,
            "loan_terms": {
                "rate_1": Decimal('20.1'),
                "rate_2": Decimal('20.2'),
                "repayment_type": {
                    "code": repayment_type.code,
                    "name": 'irrelevant',
                },
                "repayment_plan": {
                    "code": repayment_period.code,
                    "name": 'irrelevant',
                },
                "commitment_date": datetime.date.today().isoformat(),
                "repayment_first_date": datetime.date.today().isoformat(),
                "repayment_final_date": datetime.date.today().isoformat(),
            },
            "loan_status": {
                "year": 2015,
                "currency": {
                    "code": currency.code,
                    "name": 'irrelevant',
                },
                "value_date": datetime.date.today().isoformat(),
                "interest_received": 200000,
                "principal_outstanding": 1500000,
                "principal_arrears": 0,
                "interest_arrears": 0,
            },

        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/crs_add/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.CrsAdd.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])

        loan_terms = iati_models.CrsAddLoanTerms.objects.get(crs_add=instance)

        self.assertEqual(loan_terms.rate_1, data['loan_terms']['rate_1'])
        self.assertEqual(loan_terms.rate_2, data['loan_terms']['rate_2'])
        self.assertEqual(
            loan_terms.repayment_type.code,
            data['loan_terms']['repayment_type']['code'])
        self.assertEqual(
            loan_terms.repayment_plan.code,
            data['loan_terms']['repayment_plan']['code'])
        self.assertEqual(
            loan_terms.commitment_date.isoformat(),
            data['loan_terms']['commitment_date'])
        self.assertEqual(loan_terms.repayment_first_date.isoformat(),
                         data['loan_terms']['repayment_first_date'])
        self.assertEqual(loan_terms.repayment_final_date.isoformat(),
                         data['loan_terms']['repayment_final_date'])

        loan_status = iati_models.CrsAddLoanStatus.objects.get(
            crs_add=instance)

        self.assertEqual(loan_status.year, data['loan_status']['year'])
        self.assertEqual(loan_status.currency.code,
                         data['loan_status']['currency']['code'])
        self.assertEqual(loan_status.interest_received,
                         data['loan_status']['interest_received'])
        self.assertEqual(
            loan_status.principal_outstanding,
            data['loan_status']['principal_outstanding'])
        self.assertEqual(loan_status.principal_arrears,
                         data['loan_status']['principal_arrears'])
        self.assertEqual(loan_status.interest_arrears,
                         data['loan_status']['interest_arrears'])

    def test_update_crs_add(self):
        crs_add = CrsAddFactory.create()
        repayment_type = LoanRepaymentTypeFactory.create()
        repayment_period = LoanRepaymentPeriodFactory.create()
        currency = CurrencyFactory.create()

        data = {
            "activity": crs_add.activity.id,
            "loan_terms": {
                "rate_1": Decimal('20.1'),
                "rate_2": Decimal('20.2'),
                "repayment_type": {
                    "code": repayment_type.code,
                    "name": 'irrelevant',
                },
                "repayment_plan": {
                    "code": repayment_period.code,
                    "name": 'irrelevant',
                },
                "commitment_date": datetime.date.today().isoformat(),
                "repayment_first_date": datetime.date.today().isoformat(),
                "repayment_final_date": datetime.date.today().isoformat(),
            },
            "loan_status": {
                "year": 2015,
                "currency": {
                    "code": currency.code,
                    "name": 'irrelevant',
                },
                "value_date": datetime.date.today().isoformat(),
                "interest_received": 200000,
                "principal_outstanding": 1500000,
                "principal_arrears": 0,
                "interest_arrears": 0,
            },

        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/crs_add/{}?format=json".format(
                self.publisher.id, crs_add.activity.id, crs_add.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.CrsAdd.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])

        loan_terms = iati_models.CrsAddLoanTerms.objects.get(crs_add=instance)

        self.assertEqual(loan_terms.rate_1, data['loan_terms']['rate_1'])
        self.assertEqual(loan_terms.rate_2, data['loan_terms']['rate_2'])
        self.assertEqual(
            loan_terms.repayment_type.code,
            data['loan_terms']['repayment_type']['code'])
        self.assertEqual(
            loan_terms.repayment_plan.code,
            data['loan_terms']['repayment_plan']['code'])
        self.assertEqual(
            loan_terms.commitment_date.isoformat(),
            data['loan_terms']['commitment_date'])
        self.assertEqual(loan_terms.repayment_first_date.isoformat(),
                         data['loan_terms']['repayment_first_date'])
        self.assertEqual(loan_terms.repayment_final_date.isoformat(),
                         data['loan_terms']['repayment_final_date'])

        loan_status = iati_models.CrsAddLoanStatus.objects.get(
            crs_add=instance)

        self.assertEqual(loan_status.year, data['loan_status']['year'])
        self.assertEqual(loan_status.currency.code,
                         data['loan_status']['currency']['code'])
        self.assertEqual(loan_status.interest_received,
                         data['loan_status']['interest_received'])
        self.assertEqual(
            loan_status.principal_outstanding,
            data['loan_status']['principal_outstanding'])
        self.assertEqual(loan_status.principal_arrears,
                         data['loan_status']['principal_arrears'])
        self.assertEqual(loan_status.interest_arrears,
                         data['loan_status']['interest_arrears'])

    def test_delete_crs_add(self):
        crs_add = CrsAddFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/crs_add/{}?format=json".format(
                self.publisher.id, crs_add.activity.id, crs_add.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.CrsAdd.objects.get(pk=crs_add.id)


@skip
class CrsAddOtherFlagsSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_crs_add_other_flags(self):
        crs_add = CrsAddFactory.create()
        other_flags = codelist_factory.OtherFlagsFactory.create()

        data = {
            "crs_add": crs_add.id,
            "other_flags": {
                "code": other_flags.code,
                "name": 'irrelevant',
            },
            "significance": 1,
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/crs_add/{}/other_flags/?format=json".format(  # NOQA: E501
                self.publisher.id, crs_add.activity.id, crs_add.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.CrsAddOtherFlags.objects.get(
            pk=res.json()['id'])
        self.assertEqual(instance.crs_add.id, data['crs_add'])
        self.assertEqual(instance.other_flags.code,
                         data['other_flags']['code'])
        self.assertEqual(instance.significance, bool(data['significance']))

    def test_update_crs_add_other_flags(self):
        crs_add_other_flags = CrsAddOtherFlagsFactory.create()
        other_flags = codelist_factory.OtherFlagsFactory.create()

        data = {
            "crs_add": crs_add_other_flags.crs_add.id,
            "other_flags": {
                "code": other_flags.code,
                "name": 'irrelevant',
            },
            "significance": 1,
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/crs_add/{}/other_flags/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                crs_add_other_flags.crs_add.activity.id,
                crs_add_other_flags.id,
                crs_add_other_flags.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.CrsAddOtherFlags.objects.get(
            pk=res.json()['id'])
        self.assertEqual(instance.crs_add.id, data['crs_add'])
        self.assertEqual(instance.other_flags.code,
                         data['other_flags']['code'])
        self.assertEqual(instance.significance, bool(data['significance']))

    def test_delete_crs_add_other_flags(self):
        crs_add_other_flags = CrsAddOtherFlagsFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/crs_add/{}/other_flags/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                crs_add_other_flags.crs_add.activity.id,
                crs_add_other_flags.id,
                crs_add_other_flags.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.CrsAddOtherFlags.objects.get(
                pk=crs_add_other_flags.id)


@skip
class FssSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_fss(self):
        activity = ActivityFactory.create()

        data = {
            "activity": activity.id,
            "extraction_date": datetime.date.today().isoformat(),
            "priority": "1",
            "phaseout_year": 2016,
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/fss/?format=json".format(
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.Fss.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.priority, bool(data['priority']))
        self.assertEqual(instance.phaseout_year, data['phaseout_year'])

    def test_update_fss(self):
        fss = FssFactory.create()

        data = {
            "activity": fss.activity.id,
            "extraction_date": datetime.date.today().isoformat(),
            "priority": "1",
            "phaseout_year": 2016,
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/fss/{}?format=json".format(
                self.publisher.id, fss.activity.id, fss.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.Fss.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.priority, bool(data['priority']))
        self.assertEqual(instance.phaseout_year, data['phaseout_year'])

    def test_delete_fss(self):
        fss = FssFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/fss/{}?format=json".format(
                self.publisher.id, fss.activity.id, fss.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.Fss.objects.get(pk=fss.id)


@skip
class FssForecastSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_fss_forecast(self):
        fss = FssFactory.create()
        currency = CurrencyFactory.create()

        data = {
            "fss": fss.id,
            "year": 2014,
            "value_date": datetime.date.today().isoformat(),
            "currency": {
                "code": currency.code,
                "name": 'irrelevant',
            },
            "value": 10000,
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/fss/{}/forecast/?format=json".format(  # NOQA: E501
                self.publisher.id, fss.activity.id, fss.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.FssForecast.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.fss.id, data['fss'])
        self.assertEqual(instance.year, data['year'])
        self.assertEqual(instance.value_date.isoformat(), data['value_date'])
        self.assertEqual(instance.currency.code, data['currency']['code'])
        self.assertEqual(instance.value, data['value'])

    def test_update_fss_forecast(self):
        fss_forecast = FssForecastFactory.create()
        currency = CurrencyFactory.create(code="eur")

        data = {
            "fss": fss_forecast.fss.id,
            "year": 2014,
            "value_date": datetime.date.today().isoformat(),
            "currency": {
                "code": currency.code,
                "name": 'irrelevant',
            },
            "value": 10000,
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/fss/{}/forecast/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                fss_forecast.fss.activity.id,
                fss_forecast.fss.id,
                fss_forecast.id),
            data,
            format='json')

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.FssForecast.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.fss.id, data['fss'])
        self.assertEqual(instance.year, data['year'])
        self.assertEqual(instance.value_date.isoformat(), data['value_date'])
        self.assertEqual(instance.currency.code, data['currency']['code'])
        self.assertEqual(instance.value, data['value'])

    def test_delete_fss_forecast(self):
        fss_forecast = FssForecastFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/fss/{}/forecast/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                fss_forecast.fss.activity.id,
                fss_forecast.fss.id,
                fss_forecast.id),
            format='json')

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.FssForecast.objects.get(pk=fss_forecast.id)


@skip
class RelatedActivitySaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_related_activity(self):
        activity = ActivityFactory.create()
        activity2 = ActivityFactory.create(id="another-activity")
        codelist_factory.RelatedActivityTypeFactory.create()

        data = {
            "activity": activity.id,
            "ref": activity2.iati_identifier,
            "type": {
                "code": '1',
                "name": 'Parent',
            },
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/related_activities/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.RelatedActivity.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.current_activity.id, data['activity'])
        self.assertEqual(instance.ref, str(data['ref']))
        self.assertEqual(instance.ref_activity.iati_identifier, data['ref'])
        self.assertEqual(instance.type.code, data['type']['code'])

    def test_update_related_activity(self):
        related_activity = RelatedActivityFactory.create()
        activity2 = ActivityFactory.create(id="another-activity")
        type = codelist_factory.RelatedActivityTypeFactory.create(code="2")

        data = {
            "activity": related_activity.current_activity.id,
            "ref": activity2.iati_identifier,
            "type": {
                "code": type.code,
                "name": 'Parent',
            },
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/related_activities/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                related_activity.current_activity.id,
                related_activity.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.RelatedActivity.objects.get(pk=res.json()['id'])
        self.assertEqual(instance.current_activity.id, data['activity'])
        self.assertEqual(instance.ref, str(data['ref']))
        self.assertEqual(instance.ref_activity.iati_identifier, data['ref'])
        self.assertEqual(instance.type.code, data['type']['code'])

    def test_delete_related_activity(self):
        related_activity = RelatedActivityFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/related_activities/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                related_activity.current_activity.id,
                related_activity.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.RelatedActivity.objects.get(
                pk=related_activity.id)


@skip
class DocumentLinkSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_document_link(self):
        activity = ActivityFactory.create()
        file_format = codelist_factory.FileFormatFactory.create()

        data = {
            "activity": activity.id,
            "url": "https://bitcoin.org/bitcoin.pdf",
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "document_date": {
                "iso_date": datetime.date.today().isoformat(),
            },
            "format": {
                "code": file_format.code,
                "name": "random_stuff",
            }
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/document_links/?format=json".format(  # NOQA: E501
                self.publisher.id, activity.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.DocumentLink.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.url, data['url'])
        self.assertEqual(instance.iso_date.isoformat(),
                         data['document_date']['iso_date'])
        self.assertEqual(instance.file_format.code, data['format']['code'])

        instance2 = iati_models.DocumentLinkTitle.objects.get(
            document_link_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['title']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['title']['narratives'][1]['text'])

    def test_update_document_link(self):
        document_link = DocumentLinkFactory.create()
        file_format = codelist_factory.FileFormatFactory.create(
            code="application/json")

        data = {
            "activity": document_link.activity.id,
            "url": "https://bitcoin.org/bitcoin.pdf",
            "title": {
                "narratives": [
                    {
                        "text": "test1"
                    },
                    {
                        "text": "test2"
                    }
                ],
            },
            "document_date": {
                "iso_date": datetime.date.today().isoformat(),
            },
            "format": {
                "code": file_format.code,
                "name": "random_stuff",
            }
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/document_links/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link.activity.id,
                document_link.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.DocumentLink.objects.get(pk=res.json()['id'])

        self.assertEqual(instance.activity.id, data['activity'])
        self.assertEqual(instance.url, data['url'])
        self.assertEqual(instance.iso_date.isoformat(),
                         data['document_date']['iso_date'])
        self.assertEqual(instance.file_format.code, data['format']['code'])

        instance2 = iati_models.DocumentLinkTitle.objects.get(
            document_link_id=res.json()['id'])

        # order by creation time ('id')
        narratives2 = instance2.narratives.all().order_by('id')

        self.assertEqual(narratives2[0].content,
                         data['title']['narratives'][0]['text'])
        self.assertEqual(narratives2[1].content,
                         data['title']['narratives'][1]['text'])

    def test_delete_document_link(self):
        document_links = DocumentLinkFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/document_links/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_links.activity.id,
                document_links.id
            ),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.DocumentLink.objects.get(
                pk=document_links.id)


@skip
class DocumentLinkCategorySaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_document_link_category(self):
        document_link = DocumentLinkFactory.create()
        document_category = codelist_factory.DocumentCategoryFactory.create()

        data = {
            "document_link": document_link.id,
            "category": {
                "code": document_category.code,
                "name": "random_stuff",
            }
        }

        res = self.c.post(
            "/api/publishers/{}/activities/{}/document_links/{}/categories/?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link.activity.id,
                document_link.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.DocumentLinkCategory.objects.get(pk=res.json()[
                                                                'id'])

        self.assertEqual(instance.document_link.id, data['document_link'])
        self.assertEqual(instance.category.code, data['category']['code'])

    def test_update_document_link_category(self):
        document_link_category = DocumentLinkCategoryFactory.create()
        document_category = codelist_factory.DocumentCategoryFactory.create(
            code="2")

        data = {
            "document_link": document_link_category.document_link.id,
            "category": {
                "code": document_category.code,
                "name": "random_stuff",
            }
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/document_links/{}/categories/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link_category.document_link.activity.id,
                document_link_category.document_link.id,
                document_link_category.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.DocumentLinkCategory.objects.get(pk=res.json()[
                                                                'id'])

        self.assertEqual(instance.document_link.id, data['document_link'])
        self.assertEqual(instance.category.code, data['category']['code'])

    def test_delete_document_link_category(self):
        document_link_category = DocumentLinkCategoryFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/document_links/{}/categories/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link_category.document_link.activity.id,
                document_link_category.document_link.id,
                document_link_category.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.DocumentLinkCategory.objects.get(
                pk=document_link_category.id)


@skip
class DocumentLinkLanguageSaveTestCase(TestCase):
    request_dummy = RequestFactory().get('/')
    c = APIClient()

    def setUp(self):
        admin_group = OrganisationAdminGroupFactory.create()
        user = OrganisationUserFactory.create(user__username='test1')

        admin_group.organisationuser_set.add(user)

        self.publisher = admin_group.publisher

        self.c.force_authenticate(user.user)

    def test_create_language(self):
        document_link = DocumentLinkFactory.create()
        language = codelist_factory.LanguageFactory.create()

        data = {
            "document_link": document_link.id,
            "language": {
                "code": language.code,
                "name": "random_stuff",
            }
        }

        res = self.c.post(
                "/api/publishers/{}/activities/{}/document_links/{}/languages/?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link.activity.id,
                document_link.id
            ),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 201, res.json())

        instance = iati_models.DocumentLinkLanguage.objects.get(pk=res.json()[
                                                                'id'])

        self.assertEqual(instance.document_link.id, data['document_link'])
        self.assertEqual(instance.language.code, data['language']['code'])

    def test_update_language(self):
        document_link_language = DocumentLinkLanguageFactory.create()
        language = codelist_factory.LanguageFactory.create(code="2")

        data = {
            "document_link": document_link_language.document_link.id,
            "language": {
                "code": language.code,
                "name": "random_stuff",
            }
        }

        res = self.c.put(
            "/api/publishers/{}/activities/{}/document_links/{}/languages/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link_language.document_link.activity.id,
                document_link_language.document_link.id,
                document_link_language.id),
            data,
            format='json'
        )

        self.assertEqual(res.status_code, 200, res.json())

        instance = iati_models.DocumentLinkLanguage.objects.get(pk=res.json()[
                                                                'id'])

        self.assertEqual(instance.document_link.id, data['document_link'])
        self.assertEqual(instance.language.code, data['language']['code'])

    def test_delete_language(self):
        document_link_language = DocumentLinkLanguageFactory.create()

        res = self.c.delete(
            "/api/publishers/{}/activities/{}/document_links/{}/languages/{}?format=json".format(  # NOQA: E501
                self.publisher.id,
                document_link_language.document_link.activity.id,
                document_link_language.document_link.id,
                document_link_language.id),
            format='json'
        )

        self.assertEqual(res.status_code, 204)

        with self.assertRaises(ObjectDoesNotExist):
            iati_models.DocumentLinkLanguage.objects.get(
                pk=document_link_language.id)
