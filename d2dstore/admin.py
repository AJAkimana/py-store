from functools import update_wrapper

from django.contrib.admin import ModelAdmin as BaseModelAdmin


class CustomModelAdmin(BaseModelAdmin):
	def has_change_permission(self, request, obj=None):
		if getattr(self, '__detail_view', None):
			return False
		return super().has_change_permission(request, obj)

	def detail_view(self, request, object_id, form_url='', extra_context=None):
		setattr(self, '__detail_view', True)
		# Custom template for detail view
		org_change_form_template = self.change_form_template
		self.change_form_template = self.detail_view_template or self.change_form_template
		ret = self.changeform_view(request, object_id, form_url, extra_context)
		self.change_form_template = org_change_form_template
		delattr(self, '__detail_view')
		return ret

	def get_urls(self):
		urls = super().get_urls()
		# add detail-view for the object
		from django.urls import path

		def wrap(view):
			def wrapper(*args, **kwargs):
				return self.admin_site.admin_view(view)(*args, **kwargs)

			wrapper.model_admin = self
			return update_wrapper(wrapper, view)

		info = self.model._meta.app_label, self.model._meta.model_name
		# Replace the backwards compatibility (Django<1.9) change view
		# for the detail view.
		urls[len(urls) - 1] = path('<path:object_id>/', wrap(self.detail_view), name='%s_%s_detail' % info)
		return urls
