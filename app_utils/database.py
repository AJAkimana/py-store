import re

from django.db import transaction, IntegrityError, DatabaseError, OperationalError
from .error_handler import errors


class SaveContextManager:
    """
       Manage database exceptions during saving and updating actions.

       Args:
           model_instance(class instance): Holds the instance to be saved/updated.
           kwargs : Hold optional keyword arguments.

       Attributes:
           model: Holds the model for the instance we are saving/updating.
           field: Holds the unique field in the model.
           value: Holds value for the unique field.
           message: Holds a custom error message.
           error: Holds a error type to raise incase it's not GraphQlError.

       Returns:
           model_instance: If the action(save/update) is successful.
           error: Else expection is raised with appropriate message.
       """

    def __init__(self, model_instance, **kwargs):
        self.model_instance = model_instance
        self.model = kwargs.get('model', None)
        self.field = kwargs.get('field', None)
        self.value = kwargs.get('value', None)
        self.message = kwargs.get('message', None)
        self.error = kwargs.get('error', None)

    def __enter__(self):
        soft_deleted = True
        while soft_deleted:
            try:
                with transaction.atomic():
                    self.model_instance.save()
                    soft_deleted = False
                return self.model_instance
            except IntegrityError as e:
                if self.field is None and self.value is None:
                    self.field, self.value = self.get_model_value(str(e))
                if 'violates foreign key constraint' in str(e):
                    model_name = re.findall(
                        r'[table\s]"[a-zA-Z_]+',
                        str(e))[-1].split('_')[-1].capitalize()
                    errors.db_object_do_not_exists(
                        model_name, 'id', self.value, error_type=self.error)
                object_in_db = self.model.all_objects.get(
                    **{self.field: self.value})
                if object_in_db.deleted_at is None:
                    if self.message is not None:
                        errors.custom_message(
                            self.message, error_type=self.error)
                    errors.check_conflict(
                        self.model.__name__, self.field, self.value,
                        error_type=self.error
                    )
                new_value = f'{self.value}_{str(object_in_db.deleted_at)}'
                setattr(object_in_db, self.field, new_value)
                object_in_db.save()
                self.field = self.value = None
            except (DatabaseError, OperationalError) as e:
                message = f'Something went wrong, {str(e)}'
                errors.custom_message(message, error_type=self.error)

    def __exit__(self, exception_type, exception_value, traceback):
        return False

    def get_model_value(self, error):
        field_value = re.findall(r'[0-9a-zA-Z_+\s.@]+[)=]', error)
        field = field_value[0].replace(")", "").strip()
        value = field_value[-1].replace(")", "").strip()
        return field, value
