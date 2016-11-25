from mzml2isa import parsing, mzml, isa
import pronto


if __name__ == '__main__':
    from pronto import utils    
    parsing.main()


    # this tmp list is so for automated checking
    # of code sees that we are using the imports
    # really they are just required for pyinstaller
    tmp = [mzml, isa, pronto]
