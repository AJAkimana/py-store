from django.db import models
from django.utils import timezone


class BaseQuerySet(models.QuerySet):
    """
    Custom queryset for BaseModel
    """
    def delete(self):
        return super().update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class BaseManager(models.Manager):
    """
    Custom manager class for BaseModel.
    Attributes:
        alive_only(bool): Used to specify whether to return all
                          objects(soft-deleted inclusive) or not.
    """

    def __init__(self, *args, **kwargs):
        self.alive_only = kwargs.pop('alive_only', True)
        super(BaseManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.alive_only:
            return BaseQuerySet(self.model).filter(deleted_at=None)
        return BaseQuerySet(self.model)

    def hard_delete(self):
        return self.get_queryset().hard_delete()
