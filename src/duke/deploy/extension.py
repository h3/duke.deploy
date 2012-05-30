from duke.deploy.common import memoize, WorkingCopies, Config, workingcopytypes
import logging
import os
import re
import sys


FAKE_PART_ID = '_duke.deploy'

logger = logging.getLogger("duke.deploy")


class Source(dict):
    def exists(self):
        return os.path.exists(self['path'])


class Extension(object):
    def __init__(self, buildout): #
        self.buildout = buildout
        self.buildout_dir = buildout['buildout']['directory']
        self.executable = sys.argv[0]

    @memoize
    def get_config(self): #
        return Config(self.buildout_dir)

    def get_workingcopies(self):
        return WorkingCopies(self.get_servers())

    @memoize
    def get_config_dir(self): #
        config_dir = self.buildout['buildout'].get('config-dir', 'deploy')
        if not os.path.isabs(config_dir):
            config_dir = os.path.join(self.buildout_dir, config_dir)
        if os.path.isdir(self.buildout_dir) and not os.path.isdir(config_dir):
            logger.info('Creating missing conf dir %s.' % config_dir)
            os.mkdir(config_dir)
            # TODO: copy templates
        return config_dir

    @memoize
    def get_servers(self):
        config_dir = self.get_config_dir()
        configs = {}
        servers_section = self.buildout['buildout'].get('servers', None)
        if servers_section is None:
            return None
        section = self.buildout.get(servers_section, {})
        for name in section:
            info = section[name].split()
            options = []
            option_matcher = re.compile(r'[a-zA-Z0-9-]+=.*')
            print name
            print "++++++++++++"
           #for index, item in reversed(list(enumerate(info))):
           #    if option_matcher.match(item):
           #        del info[index]
           #        options.append(item)
           #options.reverse()
           #if len(info) < 2:
           #    logger.error("The source definition of '%s' needs at least the repository kind and URL." % name)
           #    sys.exit(1)
           #kind = info[0]
           #if kind not in workingcopytypes:
           #    logger.error("Unknown repository type '%s' for source '%s'." % (kind, name))
           #    sys.exit(1)
           #url = info[1]

           #for rewrite in self.get_config().rewrites:
           #    if len(rewrite) == 2 and url.startswith(rewrite[0]):
           #        url = "%s%s" % (rewrite[1], url[len(rewrite[0]):])

           #path = None
           #if len(info) > 2:
           #    if '=' not in info[2]:
           #        logger.warn("You should use 'path=%s' to set the path." % info[2])
           #        path = os.path.join(info[2], name)
           #        if not os.path.isabs(path):
           #            path = os.path.join(self.buildout_dir, path)
           #        options[:0] = info[3:]
           #    else:
           #        options[:0] = info[2:]

           #if path is None:
           #    source = Source(kind=kind, name=name, url=url)
           #else:
           #    source = Source(kind=kind, name=name, url=url, path=path)

           #for option in options:
           #    key, value = option.split('=', 1)
           #    if not key:
           #        raise ValueError("Option with no name '%s'." % option)
           #    if key in source:
           #        raise ValueError("Key '%s' already in source info." % key)
           #    if key == 'path':
           #        value = os.path.join(value, name)
           #        if not os.path.isabs(value):
           #            value = os.path.join(self.buildout_dir, value)
           #    if key == 'full-path':
           #        if not os.path.isabs(value):
           #            value = os.path.join(self.buildout_dir, value)
           #    if key == 'egg':
           #        if value.lower() in ('true', 'yes', 'on'):
           #            value = True
           #        elif value.lower() in ('false', 'no', 'off'):
           #            value = False
           #    source[key] = value
           #if 'path' not in source:
           #    if 'full-path' in source:
           #        source['path'] = source['full-path']
           #    else:
           #        source['path'] = os.path.join(sources_dir, name)

           #sources[name] = source

        return sources

    @memoize
    def get_auto_checkout(self):
        packages = set(self.get_servers().keys())

        auto_checkout = set(
            self.buildout['buildout'].get('auto-checkout', '').split()
        )
        if '*' in auto_checkout:
            auto_checkout = packages

        if not auto_checkout.issubset(packages):
            diff = list(sorted(auto_checkout.difference(packages)))
            if len(diff) > 1:
                pkgs = "%s and '%s'" % (", ".join("'%s'" % x for x in diff[:-1]), diff[-1])
                logger.error("The packages %s from auto-checkout have no source information." % pkgs)
            else:
                logger.error("The package '%s' from auto-checkout has no source information." % diff[0])
            sys.exit(1)

        return auto_checkout

    def get_deploy_info(self):
        auto_checkout = self.get_auto_checkout()
        sources = self.get_servers()
        deploy = self.buildout['buildout'].get('deploy', '')
        versions_section = self.buildout['buildout'].get('versions')
        versions = self.buildout.get(versions_section, {})
        develeggs = {}
        for path in deploy.split():
            # strip / from end of path
            head, tail = os.path.split(path.rstrip('/'))
            develeggs[tail] = path
        config_deploy = self.get_config().deploy
        for name in sources:
            source = sources[name]
            if source.get('egg', True) and name not in develeggs:
                path = sources[name]['path']
                status = config_deploy.get(name, name in auto_checkout)
                if os.path.exists(path) and status:
                    if name in auto_checkout:
                        config_deploy.setdefault(name, 'auto')
                    else:
                        if status == 'auto':
                            if name in config_deploy:
                                del config_deploy[name]
                                continue
                        config_deploy.setdefault(name, True)
                    develeggs[name] = path
                    if name in versions:
                        del versions[name]
        deploy = []
        for path in develeggs.itervalues():
            if path.startswith(self.buildout_dir):
                deploy.append(path[len(self.buildout_dir)+1:])
            else:
                deploy.append(path)
        return deploy, develeggs, versions


    def add_fake_part(self):
        if FAKE_PART_ID in self.buildout._raw:
            logger.error("The buildout already has a '%s' section, this shouldn't happen" % FAKE_PART_ID)
            sys.exit(1)
        self.buildout._raw[FAKE_PART_ID] = dict(
            recipe='zc.recipe.egg',
            eggs='duke.deploy',
        )
        # insert the fake part
        parts = self.buildout['buildout']['parts'].split()
        parts.insert(0, FAKE_PART_ID)
        self.buildout['buildout']['parts'] = " ".join(parts)

    def __call__(self):
        config = self.get_config()

        # store arguments when running from buildout
        if os.path.split(self.executable)[1] in ('buildout', 'buildout-script.py'):
            config.buildout_args = list(sys.argv)

        auto_checkout = self.get_auto_checkout()

        root_logger = logging.getLogger()
        workingcopies = self.get_workingcopies()
        always_checkout = self.get_always_checkout()
        always_accept_server_certificate = self.get_always_accept_server_certificate()
        (deploy, develeggs, versions) = self.get_deploy_info()

        packages = set(auto_checkout)
        sources = self.get_servers()
        for pkg in develeggs:
            if pkg in sources and sources[pkg].get('update'):
                packages.add(pkg)

        offline = self.buildout['buildout'].get('offline', '').lower() == 'true'
        workingcopies.checkout(sorted(packages),
                               verbose=root_logger.level <= 10,
                               update=always_checkout,
                               always_accept_server_certificate=always_accept_server_certificate,
                               offline=offline)

        # get updated info after checkout
        (deploy, develeggs, versions) = self.get_deploy_info()

        if versions:
            import zc.buildout.easy_install
            zc.buildout.easy_install.default_versions(dict(versions))

        self.buildout['buildout']['deploy'] = "\n".join(deploy)

        self.add_fake_part()

        config.save()


def extension(buildout=None):
    return Extension(buildout)()
