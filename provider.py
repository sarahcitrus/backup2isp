from steek import Steek

class Provider:
  @staticmethod
  def getInstance ( name, config ):
    if name == "Virgin Media":
      return Steek(config)