# Development Environment

To increase predicability, it is recommended
that ```tor-async-util``` development be done on a [Vagrant](http://www.vagrantup.com/) provisioned
[VirtualBox](https://www.virtualbox.org/)
VM running [Ubuntu 14.04](http://releases.ubuntu.com/14.04/).
Below are the instructions for spinning up such a VM.

Spin up a VM using [create_dev_env.sh](create_dev_env.sh)
(instead of using ```vagrant up``` - this is the only step
that standard vagrant commands aren't used - after provisioning
the VM you will use ```vagrant ssh```, ```vagrant halt```,
```vagrant up```, ```vagrant status```, etc).

```bash
> ./create_dev_env.sh simonsdave simonsdave@gmail.com ~/.ssh/id_rsa.pub ~/.ssh/id_rsa
Bringing machine 'default' up with 'virtualbox' provider...
==> default: Importing base box 'trusty'...
.
.
.
>
```

SSH into the VM.

```bash
> vagrant ssh
Welcome to Ubuntu 14.04 LTS (GNU/Linux 3.13.0-27-generic x86_64)

 * Documentation:  https://help.ubuntu.com/

 System information disabled due to load higher than 1.0

  Get cloud support with Ubuntu Advantage Cloud Guest:
    http://www.ubuntu.com/business/services/cloud

0 packages can be updated.
0 updates are security updates.


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
