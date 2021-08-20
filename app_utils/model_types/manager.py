import graphene


class DbBackupType(graphene.ObjectType):
	message = graphene.String()
