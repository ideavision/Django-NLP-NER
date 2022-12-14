from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

import spacy
import en_core_web_sm
from spacy import displacy
import re

# Load spacy english model -> https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-2.3.1/en_core_web_sm-2.3.1.tar.gz#egg=en_core_web_sm
nlp = spacy.load('en_core_web_sm')

# https://crisislex.org -> Load crisis and disaster lexicon 
lexicon = []
with open('assets/CrisisLexRec.txt', 'r') as file:
			lexicon = file.read().splitlines()

# Test data
# {"text":"Floods are one of the most common hazards in the United States. They occur when land that is normally dry experiences an overflow of water."}

# Functions
def get_event_format(entities):

	event = {'WHERE': [], 'WHO': [], 'WHEN': [], 'WHAT':entities['WHAT']}

	if 'LOC' in entities:
		event['WHERE'].extend(entities['LOC'])
	if 'GPE' in entities:
		event['WHERE'].extend(entities['GPE'])
	if 'FAC' in entities:
		event['WHERE'].extend(entities['FAC'])
	if 'PERSON' in entities:
		event['WHO'].extend(entities['PERSON'])
	if 'ORG' in entities:
		event['WHO'].extend(entities['ORG'])
	if 'NORP' in entities:
		event['WHO'].extend(entities['NORP'])
	if 'DATE' in entities:
		event['WHEN'].extend(entities['DATE'])
	if 'TIME' in entities:
		event['WHEN'].extend(entities['TIME'])

	return event

# views
def index(request):
    return HttpResponse("Hey, You're at the API index : get_4ww_event(text) => WHAT-WHERE-WHO-WHEN")


@api_view(['GET'])
def get_4w_event(request):
	entities = {}

	text = request.GET['text']

	if request.method == 'GET':
		doc = nlp(text)

		for ent in doc.ents:
			if ent.label_ in entities:
				if ent.text not in entities[ent.label_]:
					entities[ent.label_].append(ent.text)
			else:
				entities[ent.label_] = [ent.text]

		if 'EVENT' in entities:
			entities['WHAT'] = entities['EVENT']
		else:
			entities['WHAT'] = []
	
		preprocessed_txt = text.lower()
		preprocessed_txt = re.sub(r'[^\w\s]', '', preprocessed_txt)
		for lex in lexicon:
			if lex in preprocessed_txt and lex not in entities['WHAT']:
				entities['WHAT'].append(lex)

	return Response(get_event_format(entities))