# django-bakery

A set of helpers for baking your Django site out as flat files

## Why and what for

The code documented here is intended to make it easier to save every page gen­er­ated by a data­base-backed site as a flat file. This allows you to host the site us­ing a stat­ic-file ser­vice like [Amazon S3](http://en.wikipedia.org/wiki/Amazon_S3).

We call this pro­cess “bak­ing.” It’s our path to cheap­, stable host­ing for simple sites. We've used it for pub­lish­ing [elec­tion res­ults](http://graphics.latimes.com/2012-election-gop-results-map-iowa/), [timelines](http://timelines.latimes.com/complete-guide-lafd-hiring-controversy/), [doc­u­ments](http://documents.latimes.com/barack-obama-long-form-birth-certificate/), [in­ter­act­ive tables](http://spreadsheets.latimes.com/city-appointees-tied-garcetti/), [spe­cial pro­jects](http://graphics.latimes.com/flight-from-rage/) and [numerous](http://graphics.latimes.com/towergraphic-washington-landslide-victims/) [other](http://graphics.latimes.com/how-fast-is-lafd/) [things](http://graphics.latimes.com/picksheet-critics-picks-april-4-10-2014/).

The sys­tem comes with some ma­jor ad­vant­ages, like:

1. No data­base crashes
2. Zero serv­er con­fig­ur­a­tion and up­keep
3. No need to op­tim­ize your app code
4. You don’t pay to host CPUs, only band­width
5. An off­line ad­min­is­tra­tion pan­el is more se­cure
6. Less stress (This one can change your life)

There are draw­backs. For one, you have to integrate the "bakery" in­to your code base. More im­port­ant, a flat site can only be so com­plex. No on­line data­base means your site is all read and no write, which means no user-gen­er­ated con­tent and no com­plex searches.

[Django's class-based views](https://docs.djangoproject.com/en/dev/topics/class-based-views/) are at the heart of our approach. Putting all the pieces together is a little tricky at first, particularly if you haven't studied [the Django source code](https://github.com/django/django/tree/master/django/views/generic) or lack experience [working with Python classes](http://www.diveintopython.net/object_oriented_framework/defining_classes.html) in general. But once you figure it out, you can do all kinds of crazy things: Like configuring Django to bake out your entire site with a single command.

Here's how.

## Documentation

```{toctree}
:maxdepth: 1

gettingstarted
commonchallenges
buildableviews
buildablemodels
buildablefeeds
settingsvariables
managementcommands
credits
```

## In the wild

- Hundreds of Los Angeles Times custom pages at [latimes.com/projects](http://www.latimes.com/projects/) and [graphics.latimes.com](http://graphics.latimes.com/)
- The California Civic Data Coalition's [data downloads](https://calaccess.californiacivicdata.org/downloads/latest/)
- [A](https://apps.statesman.com/votetracker/entities/austin-city-council/) [series](https://apps.statesman.com/sxsw/2017/) [of](https://apps.statesman.com/question-of-restraint/data/) [projects](https://apps.statesman.com/homicides/) [by](https://apps.statesman.com/council-candidate-explorer/election/2016/) [the](https://apps.statesman.com/austin360/eats/) [Austin American Statesman](https://apps.statesman.com/austin360/booze-guide/)
- The Dallas Morning News' [legislative tracker](http://interactives.dallasnews.com/2017/the-85th/)
- Newsday's [police misconduct investigation](http://data.newsday.com/crime/police-misconduct/)
- Southern California Public Radio's [water report tracker](http://projects.scpr.org/applications/monthly-water-use/)
- The Daily Californian's [sexual misconduct case tracker](http://projects.dailycal.org/misconduct/)
- The [pretalx](https://pretalx.org) open-source conference management system
- The [static-site extension](https://github.com/moorinteractive/wagtail-bakery) to the Wagtail content management system

Have you used django bakery for something cool? Send a link to [b@palewi.re](mailto:b@palewi.re) and we will add it to this list.

## Considering alternatives

If you are seeking to "bake" out a very simple site, maybe you don't have a database or only a single page, it is quicker
to try [Tarbell](https://github.com/tarbell-project/tarbell) or [Frozen-Flask](https://pythonhosted.org/Frozen-Flask/), which don't require all
the overhead of a full Django installation.

This library is better suited for projects that require a database, want to take advantage of other Django features (like the administration panel)
or require more complex views.

## Contributing

- Code repository: [https://github.com/palewire/django-bakery/](https://github.com/palewire/django-bakery/)
- Issues: [https://github.com/palewire/django-bakery/issues](https://github.com/palewire/django-bakery/issues)
- Packaging: [https://pypi.python.org/pypi/django-bakery](https://pypi.python.org/pypi/django-bakery)
