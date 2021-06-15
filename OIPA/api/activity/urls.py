from django.conf import settings
from django.conf.urls import url
from django.views.decorators.cache import cache_page

import api.activity.views
import api.sector.views

app_name = 'api'
urlpatterns = [
    url(r'^$',
        api.activity.views.ActivityList.as_view(),
        name='activity-list'),
    url(r'^aggregations/',
        cache_page(
            settings.API_CACHE_SECONDS
        )(api.activity.views.ActivityAggregations.as_view()),
        name='activity-aggregations'),
    url(r'^(?P<pk>\d+)/transactions/$',
        api.activity.views.ActivityTransactionList.as_view(),
        name='activity-transactions'),
    url(r'^(?P<pk>\d+)/$',
        api.activity.views.ActivityDetail.as_view(),
        name='activity-detail'),
    url(r'^(?P<iati_identifier>[:\/\.\ \w-]+)/transactions/$',
        api.activity.views.ActivityTransactionListByIatiIdentifier.as_view(),
        name='activity-transactions-by-iati-identifier'),
    url(r'^(?P<iati_identifier>[:\/\.\ \w-]+)/$',
        api.activity.views.ActivityDetailByIatiIdentifier.as_view(),
        name='activity-detail-by-iati-identifier'),
    url(r'^(?P<pk>\d+)/transactions/(?P<id>[^@$&+,/:;=?]+)$',
        api.activity.views.ActivityTransactionDetail.as_view(),
        name='activity-transaction-detail'),
]
