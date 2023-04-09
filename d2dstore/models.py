import re
import uuid
from django.db import models, IntegrityError, DatabaseError, OperationalError
from django.utils import timezone

# from app_utils.error_handler import errors
# from apps.users.models import User
from d2dstore.manager import BaseManager


class BaseModel(models.Model):
	"""
	General model to implement common fields and soft delete

	Attributes:
	created_at: Holds date/time for when an object was created.
	updated_at: Holds date/time for last update on an object.
	deleted_at: Holds date/time for soft-deleted objects.
	deleted_by: Holds users who soft-deleted an objects.
	objects: Return objects that have not been soft-deleted.
	all_objects: Return all objects(soft-deleted inclusive)
	"""
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	created_at = models.DateTimeField(default=timezone.now, null=True)
	updated_at = models.DateTimeField(default=timezone.now, null=True)
	deleted_at = models.DateTimeField(blank=True, null=True)
	# deleted_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)

	objects = BaseManager()
	all_objects = BaseManager(alive_only=False)

	class Meta:
		abstract = True

	def delete(self):
		self.deleted_at = timezone.now()
		self.save()

	def hard_delete(self):
		super(BaseModel, self).delete()
