duke-deploy-django
==================

A recipe for duke to deploy django projects


Buildout
--------

::

    [deploy]
    recipe = duke.deploy
    config-dir = ${buildout:directory}/deploy/
    servers =
     demo = custom-deploy demo@mymachine.com
     beta = cpanel pony@myserver.com,pony@myserver2.com
     prod = plesk admin@myotherserver.com:3311

    [custom-deploy]
    user = www-data
    group = www-data
    document-root = /var/www/vhosts/domain.com/httpdocs/
    media-root = /var/www/vhosts/domain.com/httpdocs/media/
    static-root = /var/www/vhosts/domain.com/httpdocs/static/
    vhost-conf = /var/www/vhosts/domain.com/conf/vhost.conf
    wsgi-processes = 8
    wsgi-threads = 15
    on-deploy-done =
     ln -sf ${buildout:directory}/%(project)s/media /var/www/vhosts/%(domain)s/subdomains/beta/httpdocs/media
     chmod 777 ${buildout:directory}/%(project)s/dev.db



Configurations
--------------

::

    deploy/
      beta/
        settings.py
        vhost.conf
      prod/
        settings.py
        vhost.conf
