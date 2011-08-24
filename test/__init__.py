import sys
import os.path

root_dir = os.path.dirname(os.path.dirname(__file__))
jsonselect_dir = os.path.join(root_dir, 'jsonselect')
sys.path.append(jsonselect_dir)
