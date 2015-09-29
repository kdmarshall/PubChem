#!/usr/bin/python
__doc__ = """
[KDM 12-12-2014]

This module interacts with the PubChem RESTful web
service (PUG) and constructs a custom python object
with the returned data.
   
Contributor: Kyle Marshall
kyle.marshall@schrodinger.com
Copyright 2014 Schrodinger LLc, All Rights Reserved
"""
###############################################################################
# Packages
###############################################################################
import sys
import requests
import json
from bs4 import BeautifulSoup
from urlparse import urlparse

__all__ = ['PubChem']

###############################################################################
# Constants
###############################################################################

PUBCHEM_COMPOUND_ID_PATH = "http://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/%s/cids/JSON"
PUBCHEM_COMPOUND_PATH = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/%s/JSON"
PUBCHEM_VENDOR_PATH = "https://pubchem.ncbi.nlm.nih.gov/summary/summary.cgi?cid=%s&q=lvnd"
PUBCHEM_SYNONYMS_PATH = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/index/compound/%s/JSON/"

###############################################################################
# Classes
###############################################################################

class PubChem(object):
    """
    Class that handles the RESTful interaction with PubChem. This class
    focuses on commercially available compounds and their vendors, along
    with any patent or publication data the compound might be found in.
    """
    def __init__(self,smiles):
        """
        If the searched SMILES returns a PubChem ID, construct
        the object. If not, fill the object with null data.
        """
        self.search_smiles = smiles
        self.pubchem_compound_id = self._get_pubchem_cid()
        if self.pubchem_compound_id:
            self.canonical_smiles, self.isomeric_smiles, self.iupac = self._get_pubchem_smiles()
            self.depositor_synonyms = self._get_pubchem_synonyms()
            self.vendors = self._get_pubchem_vendors()
            self.patents = self._get_pubchem_patents()
            self.articles = self._get_pubchem_articles()
        else:
            self.canonical_smiles = None
            self.isomeric_smiles = None
            self.iupac = None
            self.depositor_synonyms = None
            self.vendors = None
            self.patents = None
            self.articles = None

    def to_dict(self):
        """
        Only public method. Turns all member variables into
        a much easier to read and use dictionary.
        """
        data = {}
        data['searched_smiles'] = self.search_smiles
        data['pubchem_compound_id'] = self.pubchem_compound_id
        data['canonical_smiles'] = self.canonical_smiles
        data['isomeric_smiles'] = self.isomeric_smiles
        data['iupac_names'] = self.iupac
        data['depositor_synonyms'] = self.depositor_synonyms
        data['vendors'] = self.vendors
        data['patents'] = self.patents
        data['articles'] = self.articles

        return data

    def __str__(self):
        return "PubChemID={cid} : {iupac} : {can_smiles} ".format(cid=self.pubchem_compound_id, iupac=self.iupac, can_smiles=self.canonical_smiles)

    def _get_pubchem_cid(self):
        """
        Returns the unique PubChem ID for 
        the searched smiles string. Returns None if 
        not found.
        """
        url = PUBCHEM_COMPOUND_ID_PATH % self.search_smiles
        try:
            response = requests.get(url)
        except requests.exceptions.HTTPError:
            return None
        cid_dict = json.loads(response.content)
        cid_list = cid_dict['IdentifierList']['CID']
        if cid_list:
            if len(cid_list) == 1:
                if cid_list[0] == 0:
                    #raise NoCompoundFoundException("SMILES %s NOT FOUND: Did not return a compound ID from Pubchem"%self.search_smiles)
                    print "SMILES %s NOT FOUND: Did not return a compound ID from Pubchem"%self.search_smiles
                    return None
                else:
                    return str(cid_list[0])
            else:
                return cid_list
        else:
            raise NoCompoundFoundException("SMILES %s NOT FOUND: Did not return a compound ID from Pubchem"%self.search_smiles)
            return None

    def _get_pubchem_smiles(self):
        """
        Returns all variations of IUPAC names
        PubChem has stored for the searched smiles.
        """
        iso_smiles = None
        can_smiles = None
        iupac_name = []
        if isinstance(self.pubchem_compound_id, basestring):
            url = PUBCHEM_COMPOUND_PATH % self.pubchem_compound_id
            try:
                response = requests.get(url)
            except requests.exceptions.HTTPError:
                return None,None,None
            pc_dict = json.loads(response.content)
            for pc in pc_dict['PC_Compounds'][0]['props']:
                if pc['urn']['label'] == 'SMILES':
                    if pc['urn']['name'] == 'Canonical':
                        can_smiles = pc['value']['sval']
                    if pc['urn']['name'] == 'Isomeric':
                        iso_smiles = pc['value']['sval']
                if pc['urn']['label'] == 'IUPAC Name':
                    iupac = pc['value']['sval']
                    if iupac not in iupac_name:
                        iupac_name.append(iupac)

            return can_smiles, iso_smiles, iupac_name
            
        elif isinstance(self.pubchem_compound_id, list):
            can_smiles_list = []
            iso_smiles_list = []
            for pubchem_id in self.pubchem_compound_id:
                url = PUBCHEM_COMPOUND_PATH % self.pubchem_compound_id
                try:
                    response = requests.get(url)
                except requests.exceptions.HTTPError:
                    return None,None,None
                pc_dict = json.loads(response.content)
                for pc in pc_dict['PC_Compounds'][0]['props']:
                    if pc['urn']['label'] == 'SMILES':
                        if pc['urn']['name'] == 'Canonical':
                            can_smiles = pc['value']['sval']
                        if pc['urn']['name'] == 'Isomeric':
                            iso_smiles = pc['value']['sval']
                    if pc['urn']['label'] == 'IUPAC Name':
                        iupac = pc['value']['sval']
                        if iupac not in iupac_name:
                            iupac_name.append(iupac)

                can_smiles_list.append(can_smiles)
                iso_smiles_list.append(iso_smiles)

            return can_smiles_list, iso_smiles_list, iupac_name
        else:
            print "Unknown PubChem Compound ID Type"
            return None,None,None

    def _get_pubchem_synonyms(self):
        """
        Returns all known compound synonyms,
        including proprietary names.
        """
        syn_list = []
        url = PUBCHEM_SYNONYMS_PATH % self._get_cid()
        try:
            response = requests.get(url)
        except requests.exceptions.HTTPError:
            return None
        pc_dict = json.loads(response.content)
        for item in pc_dict['Record']['Information']:
            try:
                syn_list = item['StringValueList']
            except:
                continue
        return syn_list
           
    def _get_pubchem_vendors(self):
        """
        Parses the PubChem DOM and finds the vendor details
        for the searched smiles. The template for returned
        info is as follows:
            {Company Name: [domain,{product_ID:product_url},...], 
            ...}
        """
        vendor_dict = {}
        url = PUBCHEM_VENDOR_PATH % self._get_cid()
        try:
            response = requests.get(url)
        except requests.exceptions.HTTPError:
            print "HTTPError has occurred with path %s"%url
            return None
        if response.text == "":
            return {}
        soup = BeautifulSoup(response.text)
        soup_list = []
        for link in soup.find_all('a'):
            link_name = link.get('name')
            if link_name == 'goSID':
                continue
            link_href = link.get('href')
            link_text = link.get_text()
            domain = ''
            try:
                parsed_uri = urlparse(link_href)
                domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
            except:
                print "Cannot parse url %s"%url
            soup_list.append((link_text,link_href,domain,link_name))

        for item in soup_list:
            if item[3] == 'goExtSource' and not vendor_dict.has_key(item[0]):
                vendor_dict[item[0]] = []
                vendor_dict[item[0]].append(item[1])
            if item[3] == 'goExtId':
                for key in vendor_dict.keys():
                    if item[2] in vendor_dict[key][0]:
                        vendor_dict[key].append({item[0]:item[1]})
                        break

        return vendor_dict

    def _get_pubchem_patents(self):
        """
        If exists, returns a list of patent dicts that
        contain the fields:
            - patentdate
            - patenturl
            - patentid
            - patenttitle
        """
        PATENT_QUERY_PATH = """https://pubchem.ncbi.nlm.nih.gov/datadicer/ddcontroller.cgi?_dc=1421875805880&cmd=query&query=%7B%22DDCompleteQuery%22%3A%7B%22queries%22%3A%5B%7B%22querytype%22%3A%22cid%22%2C%22list%22%3A%5B%22"""+self._get_cid()+"""%22%5D%2C%22operator%22%3A%22and%22%2C%22childqueries%22%3A%5B%5D%7D%5D%2C%22columns%22%3A%5B%22cid%22%2C%22patentid%22%2C%22patenttitle%22%2C%22patentdate%22%2C%22patenturl%22%5D%7D%7D&page=1&\
        start=0&limit=10&sort=%5B%7B%22property%22%3A%22patentdate%22%2C%22direction%22%3A%22DESC%22%7D%5D"""

        try:
            response = requests.get(PATENT_QUERY_PATH)
        except requests.exceptions.HTTPError:
            print "HTTPError has occurred with path %s"%PATENT_QUERY_PATH
            return None
        if response.text == "":
            return []
        else:
            return json.loads(response.text)['DDOutput']['pages']['content']


    def _get_pubchem_articles(self):
        """
        If exists, returns a list of article dicts that
        contain the fields:
            - articlejourname
            - articletitle
            - articlepubdate
            - pmid
        """
        ARTICLES_QUERY_PATH = """https://pubchem.ncbi.nlm.nih.gov/datadicer/ddcontroller.cgi?_dc=1421875657558&cmd=query&query=%7B%22DDCompleteQuery%22%3A%7B%22queries%22%3A%5B%7B%22querytype%22%3A%22cid%22%2C%22list%22%3A%5B%22"""+self._get_cid()+"""%22%5D%2C%22operator%22%3A%22and%22%2C%22childqueries%22%3A%5B%5D%7D%5D%2C%22columns%22%3A%5B%22pmid%22%2C%22articlepubdate%22%2C%22articletitle%22%2C%22articleabstract%22%2C%22articlejourname%22%2C%22articlejourabbr%22%5D%7D%7D&page=1&start=0&limit=10&sort=%5B%7B%22property%22%3A%22articlepubdate%22%2C%22direction%22%3A%22DESC%22%7D%5D"""
        try:
            response = requests.get(ARTICLES_QUERY_PATH)
        except requests.exceptions.HTTPError:
            print "HTTPError has occurred with path %s"%ARTICLES_QUERY_PATH
            return None
        if response.text == "":
            return []
        else:
            article_list = json.loads(response.text)['DDOutput']['pages']['content']
            #Remove below 3 lines if want article abstract and publication journal details returned.
            for item in article_list:
                if 'articleabstract' in item: del item['articleabstract']
                if 'articlejourabbr' in item: del item['articlejourabbr']
            return article_list

    def _get_cid(self):
        """
        For consistency, returns single CID if a string and
        returns the CID at index 0 if a list.
        """
        if isinstance(self.pubchem_compound_id, basestring):
            return self.pubchem_compound_id
        elif isinstance(self.pubchem_compound_id, list):
            return self.pubchem_compound_id[0]
        else:
            print "Unknown type for returned pubchem ID"
            return None

class NoCompoundFoundException(Exception):
    "Thrown if no compound ID returns after searching PubChem"
    pass
