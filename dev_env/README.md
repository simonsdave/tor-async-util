# Development Environment

To increase predicability, it is recommended
that ```tor-async-util``` development be done on a [Vagrant](http://www.vagrantup.com/) provisioned
[VirtualBox](https://www.virtualbox.org/)
VM running [Ubuntu 16.04](http://releases.ubuntu.com/16.04/).
Below are the instructions for spinning up such a VM.

Spin up a VM using [create_dev_env.sh](create_dev_env.sh)
(instead of using ```vagrant up``` - this is the only step
that standard vagrant commands aren't used - after provisioning
the VM you will use ```vagrant ssh```, ```vagrant halt```,
```vagrant up```, ```vagrant status```, etc).

```bash
> ./create_dev_env.sh simonsdave simonsdave@gmail.com ~/.ssh/id_rsa.pub ~/.ssh/id_rsa
Bringing machine 'default' up with 'virtualbox' provider...
==> default: Importing base box 'ubuntu/xenial64'...
.
.
.
>
```

SSH into the VM.

```bash
>vagrant ssh
Welcome to Ubuntu 16.04.4 LTS (GNU/Linux 4.4.0-119-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  Get cloud support with Ubuntu Advantage Cloud Guest:
    http://www.ubuntu.com/business/services/cloud

7 packages can be updated.
7 updates are security updates.


~>
```

Start the ssh-agent in the background.

```bash
~> eval "$(ssh-agent -s)"
Agent pid 25657
~>
```

Add SSH private key for github to the ssh-agent

```bash
~> ssh-add ~/.ssh/id_rsa_github
Enter passphrase for /home/vagrant/.ssh/id_rsa_github:
Identity added: /home/vagrant/.ssh/id_rsa_github (/home/vagrant/.ssh/id_rsa_github)
~>
```

Clone the repo.

```bash
~> git clone git@github.com:simonsdave/tor-async-util.git
Cloning into 'tor-async-util'...
remote: Counting objects: 509, done.
remote: Total 509 (delta 0), reused 0 (delta 0), pack-reused 509
Receiving objects: 100% (509/509), 89.76 KiB | 0 bytes/s, done.
Resolving deltas: 100% (295/295), done.
Checking connectivity... done.
~>
```

Configure the dev environment

```bash
~> cd tor-async-util/
~/tor-async-util> source cfg4dev
New python executable in env/bin/python
Installing setuptools, pip...done.
.
.
.
Cleaning up...
(env)~/tor-async-util>
```

Run unit tests

```bash
(env)~/tor-async-util> nosetests --with-coverage --cover-branches --cover-erase --cover-package tor_async_util
.......................................................................
Name                            Stmts   Miss Branch BrPart  Cover
-----------------------------------------------------------------
tor_async_util/__init__.py        304      0     66      0   100%
tor_async_util/jsonschemas.py       9      0      0      0   100%
-----------------------------------------------------------------
TOTAL                             313      0     66      0   100%
----------------------------------------------------------------------
Ran 71 tests in 0.620s

OK
(env)~/tor-async-util>
```

# Work-in-Progress

```bash
(env) ~/tor-async-util/tmp/tor-async-util-dev-env> docker run --rm -it simonsdave/tor-async-util-dev-env:latest bash
root@0953a6d39c66:/app# echo 'hello'
hello
root@0953a6d39c66:/app# exit
exit
(env) ~/tor-async-util/tmp/tor-async-util-dev-env>
```

```bash
docker run --rm --volume ~/tor-async-util:/app simonsdave/tor-async-util-dev-env:latest nosetests --with-coverage --cover-branches --cover-erase --cover-package tor_async_util
Coverage.py warning: --include is ignored because --source is set (include-ignored)
................................................................EEE................
======================================================================
ERROR: test_happy_path (tor_async_util.tests.unit_tests.IsLibCurlCompiledWithAsyncDNSResolverTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tor_async_util/tests/unit_tests.py", line 49, in setUp
    self.assertTrue("pycurl" not in sys.modules)
AssertionError: False is not true

======================================================================
ERROR: test_happy_version_info_array_does_not_contain_features (tor_async_util.tests.unit_tests.IsLibCurlCompiledWithAsyncDNSResolverTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tor_async_util/tests/unit_tests.py", line 49, in setUp
    self.assertTrue("pycurl" not in sys.modules)
AssertionError: False is not true

======================================================================
ERROR: test_pycurl_import_not_available (tor_async_util.tests.unit_tests.IsLibCurlCompiledWithAsyncDNSResolverTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/app/tor_async_util/tests/unit_tests.py", line 49, in setUp
    self.assertTrue("pycurl" not in sys.modules)
AssertionError: False is not true

Name                            Stmts   Miss Branch BrPart  Cover
-----------------------------------------------------------------
tor_async_util/__init__.py        345     12     74      0    97%
tor_async_util/jsonschemas.py       9      0      0      0   100%
-----------------------------------------------------------------
TOTAL                             354     12     74      0    97%
----------------------------------------------------------------------
Ran 83 tests in 1.066s

FAILED (errors=3)
```
