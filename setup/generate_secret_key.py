import os
secret_key = os.urandom(24)
print("SECRET_KEY = %r" % (secret_key))
