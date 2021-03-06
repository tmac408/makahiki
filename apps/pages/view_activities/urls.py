from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'pages.view_activities.views.index', name="activity_index"),

    url(r'^task/(\d+)/$', 'pages.view_activities.views.task', name="activity_task"),
    url(r'^task/(\d+)/add$', 'pages.view_activities.views.add_task', name="activity_add_task"),
    
    url(r'^view_codes/(\d+)/$', 'pages.view_activities.views.view_codes', name="activity_view_codes"),
    
)
