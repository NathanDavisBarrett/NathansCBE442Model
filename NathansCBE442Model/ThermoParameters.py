import numpy as np
import pyomo.environ as pyo

class ThermoParameters:
    def __init__(self):
        self.Cp = { #Specific heat capacity (kJ / kg degC)
            "PE": {
                "LIQ": 2.005
            },
            "EVOH": {
                "LIQ": 1.709
            },
            "DECALIN": {
                "LIQ": 2.229,
                "VAP": 1.775
            },
            "GVL": {
                "LIQ": 2.156
            },
            "CAT": {
                "LIQ": 0.126
            },
            "H2": {
                "VAP": 14.494,
                "LIQ": 14.494
            },
            "H2O": {
                "LIQ": 5.009,
                "VAP": 2.100
            },
            "O2": {
                "VAP": 1.0
            },
            "N2": {
                "VAP": 1.075
            },
            "CH4": {
                "VAP": 2.232
            }
        }

        self.dH_Melt = { #kJ / kg
            "PE": 500
        }

        #antoine coefficients (Pvap in atm, T in C)
        self.antoineCoefs = {
            'H2O': {
                'A': 11.6569957968225, 
                'B': 3814.444559961541, 
                'C': 227.22276227958676
            }, 
            'DECALIN': {
                'A': 8.860215800155196, 
                'B': 3442.2772092938385, 
                'C': 192.73180415509384
            }
        }

        #Heats of vaporization (kJ / kg)
        self.Hvap = {
            "H2O": 2260,
            "DECALIN": 329.11416 #https://webbook.nist.gov/cgi/cbook.cgi?ID=C493016&Mask=1A8F
        }

        #Standard Heats of combustion (kJ / kg)
        self.Hcomb = {
            "H2": 141584,
            "CH4": 55514,
            "DECALIN": 45393,
            "H2O": -45393 #TODO: INDICATE THIS!
        }

if __name__ == "__main__":
    test = ThermoParameters()