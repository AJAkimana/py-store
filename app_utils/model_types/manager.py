import graphene


class DbBackupType(graphene.ObjectType):
    message = graphene.String()


class ConvertedCurrencyType(graphene.ObjectType):
    amount = graphene.Float()
    base = graphene.String()
    converted_amount = graphene.Float()
    date = graphene.String()
    rate = graphene.Float()
    target = graphene.String()
