# {{ name }}

**{{ summary }}**

{{ name }} is a resource pack for Minecraft {{ minecraft }}.

## Features

- Feature one
- Feature two
- Feature three

{% if optifine %}
> **Requires [OptiFine](https://optifine.net/)** for all features.
{% endif %}

## Images

{{ img("overview") }}

## Installation

1. Download `{{ name }}-{{ version }}.zip`
2. Place it in your `resourcepacks/` folder
3. Enable it in Options → Resource Packs

## Links

{% if links.home %}[Home page]({{ links.home }}) · {% endif %}
{% if links.source %}[Source]({{ links.source }}) · {% endif %}
[Report a bug]({{ links.issues }})

## License

Distributed under [{{ license }}](https://spdx.org/licenses/{{ license }}).
