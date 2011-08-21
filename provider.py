from steek import Steek

class Provider:
  @staticmethod
  def getInstance ( name ):
    if name == "Virgin Media":
      return Steek()