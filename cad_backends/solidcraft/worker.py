"""Limit then exec the pinned native CLI. Invoked with Python -I in a new group."""
import os
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.execve(sys.argv[1], sys.argv[1:], os.environ)
