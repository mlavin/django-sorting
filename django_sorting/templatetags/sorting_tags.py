from django import template
from django.conf import settings

register = template.Library()

DEFAULT_SORT_UP = getattr(settings, 'DEFAULT_SORT_UP' , '&uarr;')
DEFAULT_SORT_DOWN = getattr(settings, 'DEFAULT_SORT_DOWN' , '&darr;')


sort_directions = {
    'asc': {'icon':DEFAULT_SORT_UP, 'inverse': 'desc'}, 
    'desc': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
    '': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
}


def anchor(parser, token):
    """
    Parses a tag that's supposed to be in this format: {% anchor field title %}    
    """
    bits = [b.strip('"\'') for b in token.split_contents()]
    if len(bits) < 2:
        raise template.TemplateSyntaxError, "anchor tag takes at least 1 argument"
    try:
        title = bits[2]
    except IndexError:
        title = bits[1].capitalize()
    return SortAnchorNode(bits[1].strip(), title.strip())
    

class SortAnchorNode(template.Node):
    """
    Renders an <a> HTML tag with a link which href attribute 
    includes the field on which we sort and the direction.
    and adds an up or down arrow if the field is the one 
    currently being sorted on.

    Eg.
        {% anchor name Name %} generates
        <a href="/the/current/path/?sort=name" title="Name">Name</a>

    You can also use
        {% anchor "field1,field2" Name %} to get
        <a href="/the/current/path/?sort=field1,field2" title="Name">Name</a>

        which will sort by ('field1', 'field2'). Clicking again
        will sort by ('-field1', '-field2').

    """
    def __init__(self, field, title):
        self.field = field
        self.title = title

    def render(self, context):
        request = context['request']
        getvars = request.GET.copy()
        if 'sort' in getvars:
            sortby = getvars['sort']
            del getvars['sort']
        else:
            sortby = ''
        if 'dir' in getvars:
            sortdir = getvars['dir']
            del getvars['dir']
            if sortdir not in sort_directions:
                sortdir = ''
        else:
            sortdir = ''
        if sortby == self.field:
            getvars['dir'] = sort_directions[sortdir]['inverse']
            icon = sort_directions[sortdir]['icon']
        else:
            icon = ''
        if len(getvars.keys()) > 0:
            urlappend = "&%s" % getvars.urlencode()
        else:
            urlappend = ''
        if icon:
            title = "%s %s" % (self.title, icon)
        else:
            title = self.title

        valid_fields = getattr(request, 'valid_fields', [])
        valid_fields.extend(self.field.split(","))
        setattr(request, 'valid_fields', valid_fields)
        url = '%s?sort=%s%s' % (request.path, self.field, urlappend)
        return '<a href="%s" title="%s">%s</a>' % (url, self.title, title)


def autosort(parser, token):
    bits = [b.strip('"\'') for b in token.split_contents()]
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "autosort tag takes exactly one argument"
    return SortedDataNode(bits[1])


class SortedDataNode(template.Node):
    """
    Automatically sort a queryset with {% autosort queryset %}
    """
    def __init__(self, queryset_var, context_var=None):
        self.queryset_var = template.Variable(queryset_var)
        self.context_var = context_var

    def render(self, context):
        key = self.queryset_var.var
        value = self.queryset_var.resolve(context)
        request = context['request']
        order_by = request.field
        if order_by.startswith("-"):
            direction = "-"
            order_by = order_by.lstrip("-")
        else:
            direction = ""
        sort_fields = order_by.split(",")
        valid_fields = getattr(request, 'valid_fields', [])
        # Valid fields are now defined by using the sort anchors
        # This means they must come before the auto-sort node  
        for field in sort_fields:
            if field not in valid_fields:
                context[key] = value
                break
        else:
            context[key] = value.order_by(*["%s%s" % (direction, x) for x in sort_fields])
        return ''


anchor = register.tag(anchor)
autosort = register.tag(autosort)

