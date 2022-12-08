from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from users.forms import UserRegisterForm
from .forms import ReportForm
from .models import Report
import spacy
from spacy import displacy
import re
import requests
from docx import Document
import tweepy


# Default data initialized
default_text = """An earthquake is the shifting of the Earth’s plates, which results in a sudden shaking of the ground that can last for a few seconds to a few minutes. Within seconds, mild initial shaking can strengthen and become violent. Earthquakes happen without warning and can happen at any time of year. Certain states are more prone to higher frequency of earthquakes, particularly California, Hawaii, Nevada, and Washington.Earthquakes are quite common and occur somewhere around the world every day. However, the vast majority are considered minor. The U.S. Geological Survey in 2015 reported more than 3,000 earthquakes in the United States.Even minor earthquakes that cause little damage and destruction can cause people to experience emotional distress (especially in areas not accustomed to these events). Aftershocks can continue to occur for months afterwards and can be just as stressful.\n"""

default_where = ['Earth', 'California', 'Hawaii', 'Nevada', 'Washington', 'the United States']
default_when = ['any time of year', '2015', 'months', 'a few seconds', 'a few minutes', 'seconds']
default_who = ['Earthquakes', 'The U.S. Geological Survey']
default_what = ['damage', 'warning', 'destruction', 'events']

# Load spacy english model
nlp = spacy.load('en_core_web_sm')

# Load crisis and disaster lexicon 
lexicon = []
with open('assets/CrisisLexRec.txt', 'r') as file:
			lexicon = file.read().splitlines()

# ----------------------------------------------------------------------------------------

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

# ----------------------------------------------------------------------------------------

# Main Views 

def home(request):
	doc = nlp(default_text)
	entities_html = displacy.render(doc, style="ent", minify=True)
	event = {'WHERE': default_where, 'WHO': default_who, 'WHEN': default_when, 'WHAT':default_what}
	context = {'text':default_text, 'entities_html':entities_html, 'event':event}
	return render(request, 'ner4w/home.html', context)


def extract_event(request):
	if request.method == 'POST':
		# Get text string from uploaded file, if any, two formats allowed: .txt and .docx - else get text string from textarea
		if request.FILES:
			if str(request.FILES['report_file']).endswith('.docx') :
				txt_word = []
				document = Document(request.FILES['report_file'])
				for para in document.paragraphs:
				    txt_word.append(para.text)
				text = '\n'.join(txt_word)
			elif str(request.FILES['report_file']).endswith('.txt') :
				text = request.FILES['report_file'].read().decode('utf-8')
		elif request.POST['text']:
		 	text = request.POST['text']
		else:
			text = "Please provide a text report or a valide report file.."

		# Extract NER entities using SpaCy pipeline
		entities = {}
		doc = nlp(text)

		for ent in doc.ents:
			if ent.label_ in entities :
				if ent.text not in entities[ent.label_]:
					entities[ent.label_].append(ent.text)
			else:
				entities[ent.label_] = [ent.text]
		if 'EVENT' in entities:
			entities['WHAT'] = entities['EVENT']
		else:
			entities['WHAT'] = []

		# Extract WHAT using lexicon file
		preprocessed_txt = text.lower()
		preprocessed_txt = re.sub(r'[^\w\s]', '', preprocessed_txt)
		for lex in lexicon:
			if lex in preprocessed_txt and lex not in entities['WHAT']:
				entities['WHAT'].append(lex)

		# Get situational event as WWWW dict 
		event = get_event_format(entities)

		# Get visualized html entities using DisplaCy
		entities_html = displacy.render(doc, style="ent", minify=True)

		context = {'text':text, 'entities_html':entities_html, 'event':event}

		# Save to database if user is authenticated
		if request.user.is_authenticated:
			report = Report(text=text, source="File", what=event['WHAT'], where=event['WHERE'], 
				when=event['WHEN'], who=event['WHO'], user=request.user)
			report.save()
	else:
		return redirect('home')

	return render(request, 'ner4w/home.html', context)


def extract_event_using_api(request):
	text_str = request.GET['text']	
	text = {"text" : text_str}
	event = requests.get('http://127.0.0.1:8000/api/get_4w_event/', params=text).json()
	doc = nlp(text_str)
	entities_html = displacy.render(doc, style="ent", minify=True)
	context = {'text':text_str, 'entities_html':entities_html, 'event':event}
	return render(request, 'ner4w/home.html', context)


def extract_events_from_twitter(request):
	events = []
	entities_htmls = []

	if request.method == 'POST':
		#Get users's hashtag
		hashtag = request.POST['hashtag']

		#Twitter auth and search for 20 tweets - Add your Twitter "CONSUMER_KEY" and "CONSUMER_SECRET"
		auth = tweepy.OAuthHandler("YOUR CONSUMER_KEY HERE ", "YOUR CONSUMER_SECRET HERE")
		api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
		searched_tweets = [tweet for tweet in tweepy.Cursor(api.search, q=hashtag, lang='en').items(20)]

		if searched_tweets :
			for tweet in searched_tweets:
				text = {"text" : tweet.text}
				event = requests.get('http://127.0.0.1:8000/api/get_4w_event/', params=text).json()
				events.append(event)

				doc = nlp(tweet.text)
				entities_html = displacy.render(doc, style="ent", minify=True)
				entities_htmls.append(entities_html)

				# Save every tweet to the database if user is authenticated
				if request.user.is_authenticated:
					report = Report(text=tweet.text, source="Twitter", what=event['WHAT'], where=event['WHERE'], 
								when=event['WHEN'], who=event['WHO'], user=request.user)
					report.save()

			context = {'hashtag':hashtag, 'events_entities': list(zip(events, entities_htmls))}
		else:
			context = {'hashtag':"Sorry, no tweets were found for this hashtag", 'events_entities': list(zip(events, entities_htmls))}
	else:
		context = {'hashtag':"#yourhashtag", 'events_entities': list(zip(events, entities_htmls))}

	return render(request, 'ner4w/fromtwitter.html', context)


# ---------------------------------------------------------------------------

# Profile views 

@login_required(login_url='login')
def profile(request):
	reports = Report.objects.all()
	return render(request, 'ner4w/profile.html', {'reports':reports})


@login_required(login_url='login')
def add_report(request):
	form = ReportForm()
	if request.method == 'POST':
		form = ReportForm(request.POST)
		if form.is_valid():
			report = form.save(commit=False)
			report.user = request.user
			report.save()
			return redirect('profile')
	context = {'form':form}
	return render(request, 'ner4w/add_report.html', context)


@login_required(login_url='login')
def update_report(request, id):
	report = Report.objects.get(id=id)
	form = ReportForm(instance=report)
	if request.method == 'POST':
		form = ReportForm(request.POST, instance=report)
		if form.is_valid():
			form.save()
			return redirect('profile')
	context = {'form':form, 'report':report}
	return render(request, 'ner4w/update_report.html', context)


@login_required(login_url='login')
def delete_report(request, id):
	report = Report.objects.get(id=id)
	if request.method == 'POST':
		report.delete()
		return redirect('profile')
	context = {'report':report}
	return render(request, 'ner4w/delete_report.html', context)