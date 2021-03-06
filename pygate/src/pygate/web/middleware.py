from pygate.core import models

class KegbotSiteMiddleware:
  def process_request(self, request):
    if not hasattr(request, 'kbsite'):
      sitename = 'default'
      if 'site' in request.GET:
        sitename = request.GET['site']
      request.kbsite = models.GatebotSite.objects.get(name=sitename)
