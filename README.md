
                # # # # #
              __#_#_#_#_#__
             {_` ` ` ` ` `_}
            _{_._._._._._._}_
           {_  D J A N G O  _}
          _{_._._._._._._._._}_
         {_    B A K E R Y    _}
     .---{_._._._._._._._._._._}---.
    (   `"""""""""""""""""""""""`   )
     `~~~~~~~~~~~~~~~~~~~~~~~~~~~~~`

# django-bakery

A set of helpers for baking your Django site out as flat files.

django-bakery provides buildable models, views, feeds, and management
commands for exporting a database-backed Django site as static files. It also
supports publishing those files to Amazon S3 and, optionally, rebuilding and
publishing objects through Celery.

## Documentation and links

- Documentation: <https://palewi.re/docs/django-bakery/>
- Source code: <https://github.com/palewire/django-bakery>
- Issues: <https://github.com/palewire/django-bakery/issues>
- Packaging: <https://pypi.org/project/django-bakery/>
- The dream, in PowerPoint form:
  <https://palewi.re/docs/django-bakery/_static/the-dream.pdf>

## Development

This project supports Python 3.11 and newer. Set up a checkout, including a
linked Git worktree, with:

```sh
make bootstrap
```

Run the fast checks with `make check`. Before opening a pull request, run
`make verify`, which also runs the tests, package checks, and strict
documentation build. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

django-bakery is released under the [MIT License](LICENSE).
