from django.conf.urls.defaults import *

urlpatterns = patterns('pygate.web.account.views',
    url(r'^$', 'account_main', name='kb-account-main'),
    url(r'^mugshot/$', 'edit_mugshot', name='account-mugshot'),
)
