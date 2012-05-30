#from duke.deploy.common import logger, memoize, WorkingCopies, Config, yesno
from duke.deploy.common import logger, memoize
from duke.deploy.utils import find_base
#from duke.deploy.extension import Extension
from zc.buildout.buildout import Buildout
import argparse
import atexit
import pkg_resources
import errno
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import textwrap

CONFIG_FILE = './duke/.duke.deploy.cfg'


class ChoicesPseudoAction(argparse.Action):

    def __init__(self, *args, **kwargs):
        sup = super(ChoicesPseudoAction, self)
        sup.__init__(dest=args[0], option_strings=list(args), help=kwargs.get('help'), nargs=0)


class ArgumentParser(argparse.ArgumentParser):
    def _check_value(self, action, value):
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            tup = value, ', '.join([repr(x) for x in sorted(action.choices) if x != 'pony'])
            msg = argparse._('invalid choice: %r (choose from %s)') % tup
            raise argparse.ArgumentError(action, msg)


class HelpFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        return self._fill_text(text, width, "").split("\n")

    def _fill_text(self, text, width, indent):
        result = []
        for line in text.split("\n"):
            for line2 in textwrap.fill(line, width).split("\n"):
                result.append("%s%s" % (indent, line2))
        return "\n".join(result)


class Command(object):
    def __init__(self, deploy):
        self.deploy = deploy

    @memoize
    def get_packages(self, args, auto_checkout=False,
                     deploy=False, checked_out=False):
        if auto_checkout:
            packages = set(self.deploy.auto_checkout)
        else:
            packages = set(self.deploy.sources)
        if deploy:
            packages = packages.intersection(set(self.deploy.develeggs))
        if checked_out:
            for name in set(packages):
                if not self.deploy.sources[name].exists():
                    packages.remove(name)
        if not args:
            return packages
        result = set()
        regexp = re.compile("|".join("(%s)" % x for x in args))
        for name in packages:
            if not regexp.search(name):
                continue
            result.add(name)

        if len(result) == 0:
            if len(args) > 1:
                regexps = "%s or '%s'" % (", ".join("'%s'" % x for x in args[:-1]), args[-1])
            else:
                regexps = "'%s'" % args[0]
            logger.error("No package matched %s." % regexps)
            sys.exit(1)

        return result


class CmdInstall(Command):
    def __init__(self, deploy):
        Command.__init__(self, deploy)
        self.parser=self.deploy.parsers.add_parser(
            "install",
            description="Deploy project to a specified stage")
        self.deploy.parsers._name_parser_map["co"] = self.deploy.parsers._name_parser_map["checkout"]
        self.deploy.parsers._choices_actions.append(ChoicesPseudoAction(
            "install", "i", help="Install project on a remote server"))
        self.parser.add_argument("-b", "--backup", dest="deploy_backup",
                               action="store_true", default=False,
                               help="""Backup before deploying""")
        self.parser.add_argument("-v", "--verbose", dest="verbose",
                               action="store_true", default=False,
                               help="""Show output.""")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        config = self.deploy.config
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout)
        try:
            workingcopies = WorkingCopies(self.deploy.sources)
            workingcopies.checkout(sorted(packages),
                                   verbose=args.verbose,
                                   always_accept_server_certificate=self.deploy.always_accept_server_certificate)
            for name in sorted(packages):
                source = self.deploy.sources[name]
                if not source.get('egg', True):
                    continue
                config.deploy[name] = True
                logger.info("Activated '%s'." % name)
            logger.warn("Don't forget to run buildout again, so the checked out packages are used as deploy eggs.")
            config.save()
        except (ValueError, KeyError), e:
            logger.error(e)
            sys.exit(1)


class CmdUpdate(Command):
    def __init__(self, deploy):
        Command.__init__(self, deploy)
        description="Perform an update one one or more remote servers"
        self.parser=self.deploy.parsers.add_parser(
            "update",
            description=description)
        self.deploy.parsers._name_parser_map["u"] = self.deploy.parsers._name_parser_map["update"]
        self.deploy.parsers._choices_actions.append(ChoicesPseudoAction(
            "update", "u", help=description))
        self.parser.add_argument("-c", "--code", dest="update_code",
                               action="store_true", default=False,
                               help="""Update the project code (svn up or git pull)""")

        self.parser.add_argument("-l", "--libraries", dest="update_libraries",
                               action="store_true", default=False,
                               help="""Update libraries (eggs and sources)""")

        self.parser.add_argument("-h", "--http-server", dest="update_httpserver",
                               action="store_true", default=False,
                               help="""Update HTTP server configurations and reload it""")

        self.parser.add_argument("-p", "--permissions", dest="update_permissions",
                               action="store_true", default=False,
                               help="""Update file and directory permissions""")

        self.parser.add_argument("-s", "--settings", dest="update_statics",
                               action="store_true", default=False,
                               help="""Update settings and reload the HTTP server""")
        self.parser.set_defaults(func=self)

    def __call__(self, args):
        config = self.deploy.config
        packages = self.get_packages(getattr(args, 'package-regexp'),
                                     auto_checkout=args.auto_checkout,
                                     checked_out=args.checked_out,
                                     deploy=args.deploy)
        changed = False
        for name in sorted(packages):
            source = self.deploy.sources[name]
            if not source.exists():
                logger.warning("The package '%s' matched, but isn't checked out." % name)
                continue
            if not source.get('egg', True):
                logger.warning("The package '%s' isn't an egg." % name)
                continue
            config.deploy[name] = True
            logger.info("Activated '%s'." % name)
            changed = True
        if changed:
            logger.warn("Don't forget to run buildout again, so the actived packages are actually used.")
        config.save()


class Remote(object):
    def __call__(self, **kwargs):
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)
        self.parser = ArgumentParser()
        version = pkg_resources.get_distribution("duke.deploy").version
        self.parser.add_argument('-v', '--version',
                                 action='version',
                                 version='duke.deploy %s' % version)
        self.parsers = self.parser.add_subparsers(title="commands", metavar="")
        CmdInstall(self)
        CmdUpdate(self)
        args = self.parser.parse_args()

        try:
            self.buildout_dir = find_base()
        except IOError, e:
            self.parser.print_help()
            logger.error("You are not in a path which has duke.deploy installed (%s)." % e)
            return

        self.config = Config(self.buildout_dir)
        self.original_dir = os.getcwd()
        atexit.register(self.restore_original_dir)
        os.chdir(self.buildout_dir)
        buildout = Buildout(self.config.buildout_settings['config_file'],
                            self.config.buildout_options,
                            self.config.buildout_settings['user_defaults'],
                            self.config.buildout_settings['windows_restart'])
        root_logger = logging.getLogger()
        root_logger.handlers = []
        root_logger.setLevel(logging.INFO)
        extension = Extension(buildout)
        self.conf = extension.get_config()
        self.servers = extension.get_servers()
        update, self.servers, versions = extension.get_deploy_info()

        args.func(args)

    def restore_original_dir(self):
        os.chdir(self.original_dir)

    @property
    def commands(self):
        commands = getattr(self, '_commands', None)
        if commands is not None:
            return commands
        self._commands = commands = dict()
        for key in dir(self):
            if key.startswith('cmd_'):
                commands[key[4:]] = getattr(self, key)
            if key.startswith('alias_'):
                commands[key[6:]] = getattr(self, key)
        return commands

    def unknown(self):
        logger.error("Unknown command '%s'." % sys.argv[1])
        logger.info("Type '%s help' for usage." % os.path.basename(sys.argv[0]))
        sys.exit(1)

remote = Remote()
