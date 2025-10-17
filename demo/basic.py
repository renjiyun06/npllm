from jinja2 import Template, meta

template = "{% raw %}{{variable}}{% endraw %}"
print(Template(template).render())