#!/usr/bin/python
# -*- coding: utf-8 -*-

################################################################################
#
#   RMG - Reaction Mechanism Generator
#
#   Copyright (c) 2002-2010 Prof. William H. Green (whgreen@mit.edu) and the
#   RMG Team (rmg_dev@mit.edu)
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the 'Software'),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.
#
################################################################################

"""

"""

import os
import os.path
import math
import logging
import numpy
from copy import copy, deepcopy

from base import Database, Entry, makeLogicNode

import rmgpy.constants as constants
from rmgpy.molecule import Molecule, Atom, Bond, Group

################################################################################

def saveEntry(f, entry):
    """
    Write a Pythonic string representation of the given `entry` in the thermo
    database to the file object `f`.
    """
    raise NotImplementedError()

def generateOldLibraryEntry(data):
    """
    Return a list of values used to save entries to the old-style RMG
    thermo database based on the thermodynamics object `data`.
    """
    raise NotImplementedError()
    
def processOldLibraryEntry(data):
    """
    Process a list of parameters `data` as read from an old-style RMG
    thermo database, returning the corresponding thermodynamics object.
    """
    raise NotImplementedError()


class SolventData():
    """
    Stores Abraham/Mintz parameters for characterizing a solvent.
    """
    def __init__(self, s_h=None, b_h=None, e_h=None, l_h=None, a_h=None,
    c_h=None, s_g=None, b_g=None, e_g=None, l_g=None, a_g=None, c_g=None):
        self.s_h = s_h
        self.b_h = b_h
        self.e_h = e_h
        self.l_h = l_h
        self.a_h = a_h
        self.c_h = c_h
        self.s_g = s_g
        self.b_g = b_g
        self.e_g = e_g
        self.l_g = l_g
        self.a_g = a_g
        self.c_g = c_g

class SolvationCorrection():
    """
    Stores corrections for enthalpy, entropy, and Gibbs free energy when a species is solvated.
    """
    def __init__(self, enthalpy=None, gibbs=None, entropy=None):
        self.enthalpy = enthalpy
        self.entropy = entropy
        self.gibbs = gibbs
            
class SoluteData():
    """
    Stores Abraham parameters to characterize a solute
    """
    def __init__(self, S=None, B=None, E=None, L=None, A=None, V=None, comment=""):
        self.S = S
        self.B = B
        self.E = E
        self.L = L
        self.A = A
        self.V = V
        self.comment = comment
    def __repr__(self):
        return "SoluteData(S={0},B={1},E={2},L={3},A={4},comment={5!r})".format(self.S, self.B, self.E, self.L, self.A, self.comment)
        
    def setMcGowanVolume(self, species):
        """
        Find and store the McGowan's Volume
        Returned volumes are in cm^3/mol/100 (see note below)
        See Table 2 in Abraham & McGowan, Chromatographia Vol. 23, No. 4, p. 243. April 1987
        doi: 10.1007/BF02311772
        
        "V is scaled to have similar values to the other
        descriptors by division by 100 and has units of (cm3mol−1/100)."
        the contibutions in this function are in cm3/mol, and the division by 100 is done at the very end.
        """
        molecule = species.molecules[0] # any will do, use the first.
        Vtot = 0

        for atom in molecule.atoms:
            if isCarbon(atom):
                thisV = 16.35
            elif (atom.element.number == 7): # nitrogen, do this way if we don't have an isElement method
                thisV = 14.39
            elif isOxygen(atom):
                thisV = thisV + 12.43
            #else if (element.equals("F"))
                #thisV = thisV + 10.48;
            elif isHydrogen(atom):
                thisV = thisV + 8.71
           #  else if (element.equals("Si"))
#                 thisV = thisV + 26.83;
#             else if (element.equals("P"))
#                 thisV = thisV + 24.87;
#             else if (element.equals("S"))
#                 thisV = thisV + 22.91;
#             else if (element.equals("Cl"))
#                 thisV = thisV + 20.95;
#             else if (element.equals("B"))
#                 thisV = thisV + 18.32;
#             else if (element.equals("Ge"))
#                 thisV = thisV + 31.02;
#             else if (element.equals("As"))
#                 thisV = thisV + 29.42;
#             else if (element.equals("Se"))
#                 thisV = thisV + 27.81;
#             else if (element.equals("Br"))
#                 thisV = thisV + 26.21;
#             else if (element.equals("Sn"))
#                 thisV = thisV + 39.35;
#             else if (element.equals("Te"))
#                 thisV = thisV + 36.14;
#             else if (element.equals("I"))
#                 thisV = thisV + 34.53;
            else:
                raise Exception()
            Vtot = Vtot + thisV

        for bond in molecule.bonds:
            Vtot = Vtot - 6.56;

        return Vtot / 100; # division by 100 to get units correct.


################################################################################


################################################################################

class SolventLibrary(Database):
    """
    A class for working with a RMG solvent library.
    """
    def __init__(self, label='', name='', shortDesc='', longDesc=''):
        Database.__init__(self, label=label, name=name, shortDesc=shortDesc, longDesc=longDesc)

    def loadEntry(self,
                  index,
                  label,
                  solvent,
                  reference=None,
                  referenceType='',
                  shortDesc='',
                  longDesc='',
                  history=None
                  ):
        self.entries[label] = Entry(
            index = index,
            label = label,
            data = solvent,
            reference = reference,
            referenceType = referenceType,
            shortDesc = shortDesc,
            longDesc = longDesc.strip(),
            history = history or [],
        )

    def load(self, path):
        """
        Load the solvent library from the given path
        """
        Database.load(self, path, local_context={'SolventData': SolventData}, global_context={})

    def saveEntry(self, f, entry):
        """
        Write the given `entry` in the solute database to the file object `f`.
        """
        return saveEntry(f, entry)
    
    def getSolventData(self, label):
        """
        Get a solvent's data from its name
        """
        return self.entries[label].data
        
        
class SoluteLibrary(Database):
    """
    A class for working with a RMG solute library.
    """
    def __init__(self, label='', name='', shortDesc='', longDesc=''):
        Database.__init__(self, label=label, name=name, shortDesc=shortDesc, longDesc=longDesc)

    def loadEntry(self,
                  index,
                  label,
                  molecule,
                  solute,
                  reference=None,
                  referenceType='',
                  shortDesc='',
                  longDesc='',
                  history=None
                  ):
        self.entries[label] = Entry(
            index = index,
            label = label,
            item = Molecule().fromAdjacencyList(molecule),
            data = solute,
            reference = reference,
            referenceType = referenceType,
            shortDesc = shortDesc,
            longDesc = longDesc.strip(),
            history = history or [],
        )
    
    def load(self, path):
        pass

    def saveEntry(self, f, entry):
        """
        Write the given `entry` in the solute database to the file object `f`.
        """
        return saveEntry(f, entry)

    def generateOldLibraryEntry(self, data):
        """
        Return a list of values used to save entries to the old-style RMG
        thermo database based on the thermodynamics object `data`.
        """
        return generateOldLibraryEntry(data)

    def processOldLibraryEntry(self, data):
        """
        Process a list of parameters `data` as read from an old-style RMG
        thermo database, returning the corresponding thermodynamics object.
        """
        return processOldLibraryEntry(data)

################################################################################

class SoluteGroups(Database):
    """
    A class for working with an RMG solute group additivity database.
    """

    def __init__(self, label='', name='', shortDesc='', longDesc=''):
        Database.__init__(self, label=label, name=name, shortDesc=shortDesc, longDesc=longDesc)

    def loadEntry(self,
                  index,
                  label,
                  group,
                  solute,
                  reference=None,
                  referenceType='',
                  shortDesc='',
                  longDesc='',
                  history=None
                  ):
        if group[0:3].upper() == 'OR{' or group[0:4].upper() == 'AND{' or group[0:7].upper() == 'NOT OR{' or group[0:8].upper() == 'NOT AND{':
            item = makeLogicNode(group)
        else:
            item = Group().fromAdjacencyList(group)
        self.entries[label] = Entry(
            index = index,
            label = label,
            item = item,
            data = solute,
            reference = reference,
            referenceType = referenceType,
            shortDesc = shortDesc,
            longDesc = longDesc.strip(),
            history = history or [],
        )
    
    def saveEntry(self, f, entry):
        """
        Write the given `entry` in the thermo database to the file object `f`.
        """
        return saveEntry(f, entry)

    def generateOldLibraryEntry(self, data):
        """
        Return a list of values used to save entries to the old-style RMG
        thermo database based on the thermodynamics object `data`.
        """
        
        return generateOldLibraryEntry(data)

    def processOldLibraryEntry(self, data):
        """
        Process a list of parameters `data` as read from an old-style RMG
        thermo database, returning the corresponding thermodynamics object.
        """
        return processOldLibraryEntry(data)

################################################################################

class SolvationDatabase(object):
    """
    A class for working with the RMG solute database.
    """

    def __init__(self):
        #self.depository = {}
        self.solventLibrary = SolventLibrary()
        self.soluteLibrary = SoluteLibrary()
        self.groups = {}
        self.local_context = {
            'SoluteData': SoluteData,
            'SolventData': SolventData
        }
        self.global_context = {}

    def __reduce__(self):
        """
        A helper function used when pickling a SoluteDatabase object.
        """
        d = {
            'libraries': self.libraries,
            'groups': self.groups,
            'libraryOrder': self.libraryOrder,
            }
        return (SoluteDatabase, (), d)

    def __setstate__(self, d):
        """
        A helper function used when unpickling a SoluteDatabase object.
        """
        #self.depository = d['depository']
        self.libraries = d['libraries']
        self.groups = d['groups']
        self.libraryOrder = d['libraryOrder']

    def load(self, path, libraries=None, depository=True):
        """
        Load the solvation database from the given `path` on disk, where `path`
        points to the top-level folder of the solvation database.
        """
        
        self.solventLibrary.load(os.path.join(path,'libraries','solvent.py'))
        self.soluteLibrary.load(os.path.join(path,'libraries','solute.py'))
         
        self.loadGroups(os.path.join(path, 'groups'))
        
    def getSolventData(self, solvent_name):
        return self.solventLibrary.getSolventData(solvent_name)
        
    def loadDepository(self, path):
        """
        Load the thermo database from the given `path` on disk, where `path`
        points to the top-level folder of the thermo database.
        """
        raise NotImplementedError()


    def loadGroups(self, path):
        """
        Load the solute database from the given `path` on disk, where `path`
        points to the top-level folder of the solute database.
        """
        logging.info('Loading Platts additivity group database from {0}...'.format(path))
        self.groups = {}
        self.groups['abraham']   =   SoluteGroups(label='abraham').load(os.path.join(path, 'abraham.py'  ), self.local_context, self.global_context)
        self.groups['nonacentered']  =  SoluteGroups(label='nonacentered').load(os.path.join(path, 'nonacentered.py' ), self.local_context, self.global_context)
   
    def save(self, path):
        """
        Save the solvation database to the given `path` on disk, where `path`
        points to the top-level folder of the solvation database.
        """
        path = os.path.abspath(path)
        if not os.path.exists(path): os.mkdir(path)
        self.saveLibraries(os.path.join(path, 'libraries'))
        self.saveGroups(os.path.join(path, 'groups'))

    def saveDepository(self, path):
        """
        Save the thermo depository to the given `path` on disk, where `path`
        points to the top-level folder of the thermo depository.
        """
        raise NotImplementedError()

    def saveLibraries(self, path):
        """
        Save the solute libraries to the given `path` on disk, where `path`
        points to the top-level folder of the solute libraries.
        """
        if not os.path.exists(path): os.mkdir(path)
        for library in self.libraries.values():
            library.save(os.path.join(path, '{0}.py'.format(library.label)))

    def saveGroups(self, path):
        """
        Save the solute groups to the given `path` on disk, where `path`
        points to the top-level folder of the solute groups.
        """
        if not os.path.exists(path): os.mkdir(path)
        self.groups['abraham'].save(os.path.join(path, 'abraham.py'))
        self.groups['nonacentered'].save(os.path.join(path, 'nonacentered.py'))

    def loadOld(self, path):
        """
        Load the old RMG solute database from the given `path` on disk, where
        `path` points to the top-level folder of the old RMG database.
        """
        # The old database does not have a depository, so create an empty one
        # self.depository = {}
        # self.depository['stable']  = ThermoDepository(label='stable', name='Stable Molecules')
        # self.depository['radical'] = ThermoDepository(label='radical', name='Radical Molecules')
        
        for (root, dirs, files) in os.walk(os.path.join(path, 'thermo_libraries')):
            if os.path.exists(os.path.join(root, 'Dictionary.txt')) and os.path.exists(os.path.join(root, 'Library.txt')):
                library = SoluteLibrary(label=os.path.basename(root), name=os.path.basename(root))
                library.loadOld(
                    dictstr = os.path.join(root, 'Dictionary.txt'),
                    treestr = '',
                    libstr = os.path.join(root, 'Library.txt'),
                    numParameters = 5,
                    numLabels = 1,
                    pattern = False,
                )
                library.label = os.path.basename(root)
                self.libraries[library.label] = library

        self.groups = {}
        self.groups['abraham'] = SoluteGroups(label='abraham', name='Platts Group Additivity Values for Abraham Solute Descriptors').loadOld(
            dictstr = os.path.join(path, 'thermo_groups', 'Abraham_Dictionary.txt'),
            treestr = os.path.join(path, 'thermo_groups', 'Abraham_Tree.txt'),
            libstr = os.path.join(path, 'thermo_groups', 'Abraham_Library.txt'),
            numParameters = 5,
            numLabels = 1,
            pattern = True,
        )

    def saveOld(self, path):
        """
        Save the old RMG Abraham database to the given `path` on disk, where
        `path` points to the top-level folder of the old RMG database.
        """
        # Depository not used in old database, so it is not saved

        librariesPath = os.path.join(path, 'thermo_libraries')
        if not os.path.exists(librariesPath): os.mkdir(librariesPath)
        for library in self.libraries.values():
            libraryPath = os.path.join(librariesPath, library.label)
            if not os.path.exists(libraryPath): os.mkdir(libraryPath)
            library.saveOld(
                dictstr = os.path.join(libraryPath, 'Dictionary.txt'),
                treestr = '',
                libstr = os.path.join(libraryPath, 'Library.txt'),
            )

        groupsPath = os.path.join(path, 'thermo_groups')
        if not os.path.exists(groupsPath): os.mkdir(groupsPath)
        self.groups['abraham'].saveOld(
            dictstr = os.path.join(groupsPath, 'Abraham_Dictionary.txt'),
            treestr = os.path.join(groupsPath, 'Abraham_Tree.txt'),
            libstr = os.path.join(groupsPath, 'Abraham_Library.txt'),
        )

    def getSoluteData(self, species):
        """
        Return the solute descriptors for a given :class:`Species`
        object `species`. This function first searches the loaded libraries
        in order, returning the first match found, before falling back to
        estimation via Platts group additivity.
        """
        soluteData = None
        
        # Check the library first
        soluteData = self.getSoluteDataFromLibrary(species, self.soluteLibrary)
        if soluteData is not None: 
           soluteData[0].comment = 'solute'
        else:
            # Solute not found in any loaded libraries, so estimate
            soluteData = self.getSoluteDataFromGroups(species)
        # Return the resulting solute parameters
        soluteData.setMcGowanVolume(species)
        return soluteData
        

    def getAllSoluteData(self, species):
        """
        Return all possible sets of Abraham solute descriptors for a given
        :class:`Species` object `species`. The hits from the library come
        first, then the group additivity  estimate. This method is useful 
         for a generic search job.
        """
        raise NotImplementedError()
        
    def getThermoDataFromDepository(self, species):
        """
        Return all possible sets of thermodynamic parameters for a given
        :class:`Species` object `species` from the depository. If no
        depository is loaded, a :class:`DatabaseError` is raised.
        """
        raise NotImplementedError()

    def getSoluteDataFromLibrary(self, species, library):
        """
        Return the set of Abraham solute descriptors corresponding to a given
        :class:`Species` object `species` from the specified solute
        `library`. If `library` is a string, the list of libraries is searched
        for a library with that name. If no match is found in that library,
        ``None`` is returned. If no corresponding library is found, a
        :class:`DatabaseError` is raised.
        """
        for label, entry in library.entries.iteritems():
            for molecule in species.molecule:
                if molecule.isIsomorphic(entry.item) and entry.data is not None:
                    return (deepcopy(entry.data), library, entry)
        return None

    def getSoluteDataFromGroups(self, species):
        """
        Return the set of Abraham solute parameters corresponding to a given
        :class:`Species` object `species` by estimation using the Platts group
        additivity method. If no group additivity values are loaded, a
        :class:`DatabaseError` is raised.
        
        It averages (linearly) over the desciptors for each Molecule (resonance isomer)
        in the Species.
        """       
        soluteData = SoluteData(0.0,0.0,0.0,0.0,0.0)
        count = 0
        comments = []
        for molecule in species.molecule:
            molecule.clearLabeledAtoms()
            molecule.updateAtomTypes()
            sdata = self.estimateSoluteViaGroupAdditivity(molecule)
            soluteData.S += sdata.S
            soluteData.B += sdata.B
            soluteData.E += sdata.E
            soluteData.L += sdata.L
            soluteData.A += sdata.A
            count += 1
            comments.append(sdata.comment)
            # print count #debugging purposes
        
        soluteData.S /= count
        soluteData.B /= count
        soluteData.E /= count
        soluteData.L /= count
        soluteData.A /= count
        soluteData.comment = "Average of {0}".format(" and ".join(comments))

        return soluteData
        
    def estimateSoluteViaGroupAdditivity(self, molecule):
        """
        Return the set of Abraham solute parameters corresponding to a given
        :class:`Molecule` object `molecule` by estimation using the Platts' group
        additivity method. If no group additivity values are loaded, a
        :class:`DatabaseError` is raised.
        """
        # For thermo estimation we need the atoms to already be sorted because we
        # iterate over them; if the order changes during the iteration then we
        # will probably not visit the right atoms, and so will get the thermo wrong
        molecule.sortVertices()

        # Create the SoluteData object
        soluteData = SoluteData(
            S = 0.277,
            B = 0.071,
            E = 0.248,
            L = 0.13,
            A = 0.003
        )

        if sum([atom.radicalElectrons for atom in molecule.atoms]) > 0: # radical species

            # Make a copy of the structure so we don't change the original
            saturatedStruct = molecule.copy(deep=True)

            # Saturate structure by replacing all radicals with bonds to
            # hydrogen atoms
            added = {}
            for atom in saturatedStruct.atoms:
                for i in range(atom.radicalElectrons):
                    H = Atom('H')
                    bond = Bond(atom, H, 'S')
                    saturatedStruct.addAtom(H)
                    saturatedStruct.addBond(bond)
                    if atom not in added:
                        added[atom] = []
                    added[atom].append([H, bond])
                    atom.decrementRadical()

            # Update the atom types of the saturated structure (not sure why
            # this is necessary, because saturating with H shouldn't be
            # changing atom types, but it doesn't hurt anything and is not
            # very expensive, so will do it anyway)
            saturatedStruct.updateConnectivityValues()
            saturatedStruct.sortVertices()
            saturatedStruct.updateAtomTypes()

            # Get solute descriptor estimates for saturated form of structure
            soluteData = self.estimateSoluteViaGroupAdditivity(saturatedStruct)
            assert soluteData is not None, "Solute data of saturated {0} of molecule {1} is None!".format(saturatedStruct, molecule)
            # Undo symmetry number correction for saturated structure
            # thermoData.S298.value_si += constants.R * math.log(saturatedStruct.symmetryNumber)

            # For each radical site, get radical correction
            # Only one radical site should be considered at a time; all others
            # should be saturated with hydrogen atoms
            for atom in added:

                # Remove the added hydrogen atoms and bond and restore the radical
                for H, bond in added[atom]:
                    saturatedStruct.removeBond(bond)
                    saturatedStruct.removeAtom(H)
                    atom.incrementRadical()

                saturatedStruct.updateConnectivityValues()
                
                
                        
                # Re-saturate
                

                # Subtract the enthalpy of the added hydrogens
            

            # Correct the entropy for the symmetry number

        else: # non-radical species
            # Generate estimate of solute data
            for atom in molecule.atoms:
                # Iterate over heavy (non-hydrogen) atoms
                if atom.isNonHydrogen():
                    # Get initial solute data from main group database
                    try:
                        self.__addGroupSoluteData(soluteData, self.groups['abraham'], molecule, {'*':atom})
                    except KeyError:
                        logging.error("Couldn't find in main abraham database:")
                        logging.error(molecule)
                        logging.error(molecule.toAdjacencyList())
                        raise
                    # Get solute data for non-atom centered groups    
                    try:
                        self.__addGroupSoluteData(soluteData, self.groups['nonacentered'], molecule, {'*':atom})
                    except KeyError: pass
        

        return soluteData

    def __addGroupSoluteData(self, soluteData, database, molecule, atom):
        """
        Determine the Platts group additivity solute data for the atom `atom`
        in the structure `structure`, and add it to the existing solute data
        `soluteData`.
        """

        node0 = database.descendTree(molecule, atom, None)

        if node0 is None:
            raise KeyError('Node not found in database.')

        # It's possible (and allowed) that items in the tree may not be in the
        # library, in which case we need to fall up the tree until we find an
        # ancestor that has an entry in the library
        node = node0
        
        while node is not None and node.data is None:
            node = node.parent
        if node is None:
            raise KeyError('Node has no parent with data in database.')
        data = node.data
        comment = node.label
        while isinstance(data, basestring) and data is not None:
            for entry in database.entries.values():
                if entry.label == data:
                    data = entry.data
                    comment = entry.label
                    break
        comment = '{0}({1})'.format(database.label, comment)

        # This code prints the hierarchy of the found node; useful for debugging
        #result = ''
        #while node is not None:
        #   result = ' -> ' + node + result
        #   node = database.tree.parent[node]
        #print result[4:]

        #if len(thermoData.Tdata.value_si) != len(data.Tdata.value_si) or any([T1 != T2 for T1, T2 in zip(thermoData.Tdata.value_si, data.Tdata.value_si)]):
            #raise ThermoError('Cannot add these ThermoData objects due to their having different temperature points.')
        
        #for i in range(7):
        #thermoData.Cpdata.value_si[i] += data.Cpdata.value_si[i]
        soluteData.S += data.S
        soluteData.B += data.B
        soluteData.E += data.E
        soluteData.L += data.L
        soluteData.A += data.A
        soluteData.comment += comment + "+"
        
        return soluteData

    
    def calcH(self, soluteData, solventData):
        delH = 1000*((soluteData.S*solventData.s_h)+(soluteData.B*solventData.b_h)+(soluteData.E*solventData.e_h)+(soluteData.L*solventData.l_h)+(soluteData.A*solventData.a_h)+solventData.c_h)  
        return delH
    
    def calcG(self, soluteData, solventData):
        logK = (soluteData.S*solventData.s_g)+(soluteData.B*solventData.b_g)+(soluteData.E*solventData.e_g)+(soluteData.L*solventData.l_g)+(soluteData.A*solventData.a_g)+solventData.c_g
        delG = -8.314*298*2.303*logK
        return delG
        
    
    def calcS(self, delG, delH):
        delS = (delH-delG)/298
        return delS
    
    def getSolvationCorrection(self, soluteData, solventData):
        correction = SolvationCorrection(0.0, 0.0, 0.0)
        correction.enthalpy = self.calcH(soluteData, solventData)
        correction.gibbs = self.calcG(soluteData, solventData)  
        correction.entropy = self.calcS(correction.gibbs, correction.enthalpy) 
        return correction