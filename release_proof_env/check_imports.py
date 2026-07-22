import strategy, state, observation, laboratory
import sys
for mod in [strategy, state, observation, laboratory]:
    if 'site-packages' not in str(mod.__file__):
        print(f'FAIL: {mod.__name__} loaded from {mod.__file__}')
        sys.exit(1)
print('SUCCESS: All modules loaded from site-packages')
