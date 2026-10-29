from django.conf import settings
from django.shortcuts import render
from graphene_django.views import GraphQLView
from graphql import ExecutionResult, GraphQLError, parse, validate
from graphql.validation import ValidationRule


def index(request):
	return render(request, "build/index.html")


class DisableIntrospection(ValidationRule):
	"""
	Reject schema introspection ('__schema', '__type').
	'__typename' stays allowed because Apollo Client adds it to every query.
	"""

	def enter_field(self, node, *_args):
		field_name = node.name.value
		if field_name.startswith('__') and field_name != '__typename':
			self.report_error(
				GraphQLError(f"Cannot query '{field_name}': introspection is disabled.", node)
			)


class AppGraphQLView(GraphQLView):
	"""GraphQL view that disables introspection outside DEBUG."""

	def execute_graphql_request(self, request, data, query, variables, operation_name, show_graphiql=False):
		if query and not settings.DEBUG:
			try:
				document = parse(query)
			except GraphQLError:
				pass  # The parent reports the syntax error
			else:
				errors = validate(self.schema.graphql_schema, document, [DisableIntrospection])
				if errors:
					return ExecutionResult(errors=errors)

		return super().execute_graphql_request(
			request, data, query, variables, operation_name, show_graphiql
		)
