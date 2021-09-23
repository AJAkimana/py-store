import graphene

from app_utils.helpers import calculate_percent, calculate_tax, calculate_gross_salary
from app_utils.model_types.store import SalaryType, FacilityType


class CalculateSalary(graphene.Mutation):
  message = graphene.String()
  salary = graphene.Field(SalaryType)

  class Arguments:
    gross_salary = graphene.Float()
    net_salary = graphene.Float()
    net_pay = graphene.Float()
    pension_percent = graphene.Float()
    maternity_percent = graphene.Float()
    facilities = graphene.List(FacilityType)

  def mutate(self, info, **kwargs):
    gross_salary = kwargs.get('gross_salary', 0)
    net_salary = kwargs.get('net_salary', 0)
    net_pay = kwargs.get('net_pay', 0)
    pension_percent = kwargs.get('pension_percent', 3)
    maternity_percent = kwargs.get('maternity_percent', 0.3)
    facilities = kwargs.get('facilities', [])

    if gross_salary == 0 and net_salary > 0:
      gross_salary = calculate_gross_salary(net_salary)

    pension = calculate_percent(gross_salary, pension_percent)
    maternity = calculate_percent(gross_salary, maternity_percent)
    tax = calculate_tax(gross_salary)
    net_salary = gross_salary - (pension + maternity + tax)
    net_pay = gross_salary

    salary = {
      'pension': round(pension, 2),
      'maternity': round(maternity, 2),
      'tax': round(tax, 2),
      'net_salary': round(net_salary, 2),
      'gross_salary': round(gross_salary, 2),
      'net_pay': round(net_pay, 2)
    }


    return CalculateSalary(message='Successful', salary=salary)


class ManageSystemMutations(graphene.ObjectType):
  calculate_salary = CalculateSalary.Field()
