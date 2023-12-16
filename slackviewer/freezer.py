from flask_frozen import Freezer

class CustomFreezer(Freezer):

    cf_output_dir = None

    @property
    def root(self):
        return u"{}".format(self.cf_output_dir)
    