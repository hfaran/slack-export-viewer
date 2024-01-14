from flask_frozen import Freezer
from pathlib import Path

class CustomFreezer(Freezer):

    cf_output_dir = None

    @property
    def root(self):
        # Use the specified cf_output_dir if set
        if self.cf_output_dir:
            return Path(self.cf_output_dir)
        # Otherwise, follow the default behavior of flask_frozen
        else:
            root = Path(self.app.root_path)
            return root / self.app.config['FREEZER_DESTINATION']
