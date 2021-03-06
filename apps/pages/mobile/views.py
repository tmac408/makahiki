from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, get_host

from components.activities.models import ActivityBase
from components.makahiki_base import get_current_round
from pages.view_activities.forms import *
from components.activities.models import *
from components.activities import * 
from components.makahiki_profiles.models import *
from components.makahiki_profiles import *
from datetime import timedelta, date
from time import strftime
from string import lower
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from components.quests.models import *
from components.quests import *
from django.contrib.auth import REDIRECT_FIELD_NAME
from urlparse import urljoin
from urllib import urlencode

from components.help_topics.models import HelpTopic

def index(request):
  return render_to_response("mobile/index.html", {}, context_instance=RequestContext(request))


## new design, return the category list with the tasks info
def __get_categories(user):
  categories = Category.objects.all() 

  for cat in categories:
    task_list = []
    for task in cat.activitybase_set.order_by("priority"):   
      task.is_unlock = is_unlock(user, task)
      task.is_pau = is_pau(user, task)
      if task.type == "event" or task.type == "excursion":
        task.is_event_pau = Activity.objects.get(pk=task.pk).is_event_completed()
      
      if task.type != "commitment":
        members = ActivityMember.objects.filter(user=user, activity=task).order_by("-updated_at")
      else:
        members = CommitmentMember.objects.filter(user=user, commitment=task)

      if members.count() > 0:
        task.approval = members[0]
        
      task_list.append(task)
    
    cat.task_list = task_list
    
  return categories

@login_required
def scoreboard(request):
  user = request.user
  events = get_available_events(user)
  floor = user.get_profile().floor
  
  current_round = get_current_round()
  round_name = current_round if current_round else None
  floor_standings = Floor.floor_points_leaders(num_results=10, round_name=round_name)
  profile_standings = Profile.points_leaders(num_results=10, round_name=round_name).select_related("scoreboardentry")
  user_floor_standings = floor.points_leaders(num_results=10, round_name=round_name).select_related("scoreboardentry")
  
  categories_list = __get_categories(user)

  return render_to_response("mobile/scoreboard/index.html",{
    "events": events,
    "profile":user.get_profile(),
    "floor": floor,
    "categories":categories_list,
    "current_round": round_name or "Overall",
    "floor_standings": floor_standings,
    "profile_standings": profile_standings,
    "user_floor_standings": user_floor_standings,
    "help":help,
  }, context_instance=RequestContext(request))

@login_required
def smartgrid(request):
  activities = ActivityBase.objects.order_by("priority")

  return render_to_response("mobile/smartgrid/index.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def basicenrg(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/basicenrg.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def getstarted(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/getstarted.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def movingon(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/movingon.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def lightsout(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/lightsout.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def makewatts(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/makewatts.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def potpourri(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/potpourri.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def opala(request):
  activities = ActivityBase.objects.order_by("priority")
  return render_to_response("mobile/smartgrid/opala.html", {
    "activities": activities,
  }, context_instance=RequestContext(request))

@login_required
def task(request, activity_id):
  activity = get_object_or_404(ActivityBase, id=activity_id)

  return render_to_response("mobile/smartgrid/task.html", {
    "activity": activity,
  }, context_instance=RequestContext(request))

@login_required
def sgform(request, task_id):
  task = get_object_or_404(ActivityBase, id=task_id)

  user = request.user
  
  
  floor = user.get_profile().floor
  pau = False
  question = None
  form = None
  approval = None
  can_commit = None
  member_all_count = 0
  member_floor_count = 0

  if task.type != "commitment":
    task = task.activity

    if task.type == "survey":
      member_all = ActivityMember.objects.exclude(user=user).filter(activity=task, approval_status="approved")
      members = ActivityMember.objects.filter(user=user, activity=task, approval_status="approved")
    else:
      member_all = ActivityMember.objects.exclude(user=user).filter(activity=task)
      members = ActivityMember.objects.filter(user=user, activity=task)

    if members.count() > 0:
      pau = True
      approval = members[0]
      
    if task.type == "survey":
      question = TextPromptQuestion.objects.filter(activity=task)
      form = SurveyForm(questions=question)    
      form_title = "Survey"
    else:
      form_title = "Get your points"
    
      # Create activity request form.
      if task.confirm_type == "image":
        form = ActivityImageForm()
      elif task.confirm_type == "text":
        question = task.pick_question(user.id)
        if question:
          form = ActivityTextForm(initial={"question" : question.pk},question_id=question.pk)
      elif task.confirm_type == "free":
        form = ActivityFreeResponseForm()
      else:
        form = ActivityTextForm(initial={"code" : 1})
                
      if task.type == "event" or task.type == "excursion":
        if not pau:
          form_title = "Sign up for this "+task.type
        
  else:  ## "Commitment"
    task = task.commitment
    members = CommitmentMember.objects.filter(user=user, commitment=task);
    if members.count() > 0:
      pau = True
      approval = members[0]
    
    member_all = CommitmentMember.objects.exclude(user=user).filter(commitment=task);
    form_title = "Make this commitment"
    form = CommitmentCommentForm()
    can_commit = can_add_commitments(user)
    
  users = []
  member_all_count = member_all.count()
  for member in member_all:
    if member.user.get_profile().floor == floor:
      member_floor_count = member_floor_count + 1
      users.append(member.user)
  
  if pau:
    member_all_count = member_all_count + 1
    member_floor_count = member_floor_count +1
    users.append(user)
  
  try:
    help = HelpTopic.objects.get(slug="task-details-widget-help", category="widget")
  except ObjectDoesNotExist:
    help = None
    
  display_point = True if request.GET.has_key("display_point") else False
  display_form = True if request.GET.has_key("display_form") else False
  
  return render_to_response("mobile/smartgrid/form.html", {
    "task":task,
    "pau":pau,
    "approval":approval,
    "form":form,
    "question":question,
    "member_all":member_all_count,
    "member_floor":member_floor_count,
    "users":users,
    "display_point": display_point,
    "display_form":display_form,
    "form_title": form_title,
    "can_commit":can_commit,
    "help":help,
  }, context_instance=RequestContext(request))


###################################################################################################

### Private methods.
@never_cache
def __add_commitment(request, commitment_id):
  """Commit the current user to the commitment."""
  
  commitment = get_object_or_404(Commitment, pk=commitment_id)
  user = request.user
  floor = user.get_profile().floor
  
  members = CommitmentMember.objects.filter(user=user, commitment=commitment);
  if members.count() > 0 and members[0].days_left() == 0:
    #commitment end
    member = members[0]
    member.award_date = datetime.datetime.today()
    member.save()
      
  if commitment not in user.commitment_set.all() and can_add_commitments(user):
    # User can commit to this commitment.
    member = CommitmentMember(user=user, commitment=commitment)
    member.save()
    # messages.info("You are now committed to \"%s\"" % commitment.title)

    #increase point
    user.get_profile().add_points(2, datetime.datetime.today() - datetime.timedelta(minutes=1))
    user.get_profile().save()
    
    # Check for Facebook.
    # try:
    #   import makahiki_facebook.facebook as facebook
    #   
    #   fb_user = facebook.get_user_from_cookie(request.COOKIES, settings.FACEBOOK_APP_ID, settings.FACEBOOK_SECRET_KEY)
    #   if fb_user:
    #     try:
    #       graph = facebook.GraphAPI(fb_user["access_token"])
    #       graph.put_object("me", "feed", message="I am now committed to \"%s\" in the Kukui Cup!" % commitment.title)
    #     except facebook.GraphAPIError:
    #       # Incorrect user token.
    #       pass
    #       
    # except ImportError:
    #   # Facebook not enabled.
    #   pass
        
  return HttpResponseRedirect(reverse("pages.mobile.smartgrid.views.task", args=(commitment.id,)) + "?display_point=true")

@never_cache
def __add_activity(request, activity_id):
  """Commit the current user to the activity."""

  activity = get_object_or_404(Activity, pk=activity_id)
  user = request.user
  floor = user.get_profile().floor
  
  # Search for an existing activity for this user
  if activity not in user.activity_set.all() and request.method == "POST":

    if activity.type == 'survey':
      question = TextPromptQuestion.objects.filter(activity=activity)
      form = SurveyForm(request.POST or None, questions=question)
    
      if form.is_valid():
        for i,q in enumerate(question):
          activity_member = ActivityMember(user=user, activity=activity)
##TODO.          activity_member.user_comment = form.cleaned_data["comment"]
          activity_member.question = q
          activity_member.response = form.cleaned_data['choice_response_%s' % i]
          
          if i == (len(question)-1):
            activity_member.approval_status = "approved"
            
          activity_member.save()
      else:   # form not valid
        return render_to_response("smartgrid/task.html", {
            "task":activity,
            "pau":False,
            "form":form,
            "question":question,
            "display_form":True,
            "display_point":False,
            "form_title": "Survey",
            }, context_instance=RequestContext(request))    
          
    else:
      activity_member = ActivityMember(user=user, activity=activity)
      activity_member.save()
        
      #increase point
      user.get_profile().add_points(2, datetime.datetime.today() - datetime.timedelta(minutes=1))
      user.get_profile().save()

    return HttpResponseRedirect(reverse("pages.mobile.smartgrid.views.task", args=(activity.id,)) + "?display_point=true")

@never_cache
def __request_activity_points(request, activity_id):
  """Creates a request for points for an activity."""
  
  activity = get_object_or_404(Activity, pk=activity_id)
  user = request.user
  floor = user.get_profile().floor
  question = None
  activity_member = None
  
  try:
    # Retrieve an existing activity member object if it exists.
    activity_member = ActivityMember.objects.get(user=user, activity=activity)
    if activity_member.award_date:
      # messages.info("You have already received the points for this activity.")
      return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.id,)))
      
  except ObjectDoesNotExist:
    pass # Ignore for now.

  if request.method == "POST":
    if activity.confirm_type == "image":
      form = ActivityImageForm(request.POST, request.FILES)
    elif activity.confirm_type == "free":
      form = ActivityFreeResponseForm(request.POST)
    else:
      form = ActivityTextForm(request.POST)
    
    ## print activity.confirm_type
    if form.is_valid():
      if not activity_member:
        activity_member = ActivityMember(user=user, activity=activity)
      
      activity_member.user_comment = form.cleaned_data["comment"]
      # Attach image if it is an image form.
      if form.cleaned_data.has_key("image_response"):
        path = activity_image_file_path(user=user, filename=request.FILES['image_response'].name)
        activity_member.image = path
        
        new_file = activity_member.image.storage.save(path, request.FILES["image_response"])
        
        activity_member.approval_status = "pending"

      elif activity.confirm_type == "code":
        # Approve the activity (confirmation code is validated in forms.ActivityTextForm.clean())
        code = ConfirmationCode.objects.get(code=form.cleaned_data["response"])
        code.is_active = False
        code.save()
        activity_member.approval_status = "approved" # Model save method will award the points.
        points = activity_member.activity.point_value
        
      # Attach text prompt question if one is provided
      elif form.cleaned_data.has_key("question"):
        activity_member.question = TextPromptQuestion.objects.get(pk=form.cleaned_data["question"])
        activity_member.response = form.cleaned_data["response"]
        activity_member.approval_status = "pending"
                
      elif activity.confirm_type == "free":
        activity_member.response = form.cleaned_data["response"]
        activity_member.approval_status = "pending"

      activity_member.save()
          
      return HttpResponseRedirect(reverse("pages.mobile.smartgrid.views.task", args=(activity.id,)) + "?display_point=true")
    
    if activity.confirm_type == "text":
      question = activity.pick_question(user.id)
      ##if question:
      ##  form = ActivityTextForm(initial={"question" : question.pk}, question_id=question.pk)
      
    return render_to_response("smartgrid/task.html", {
    "task":activity,
    "pau":False,
    "form":form,
    "question":question,
    "member_all":0,
    "member_floor":0,
    "display_form":True,
    "display_point":False,
    "form_title": "Get your points",
    }, context_instance=RequestContext(request))    


###################################################################################################


@login_required
def sgadd(request, task_id):
  
  task = ActivityBase.objects.get(id=task_id)

  if task.type == "commitment":
    return __add_commitment(request, task_id)
    
  if task.type == "activity":
    return __request_activity_points(request, task_id)
  elif task.type == "survey":
    return __add_activity(request, task_id)
  else:
    task = Activity.objects.get(pk=task.pk)
    if task.is_event_completed():
      return __request_activity_points(request, task_id)
    else:  
      return __add_activity(request, task_id)
    
   
  

def landing(request):
  return render_to_response("mobile/landing.html", {}, context_instance=RequestContext(request))
 
class EventDay:
  def __init__(self):
    self.date = ''
    self.datestring = ''
    self.eventlist = []
    self.count = 0
  def __str__(self):
    return "obj= " + str(self.date) + " " +  " " + str(self.eventlist)

#used for sorting lists of events
def get_date(obj):
  return obj.event_date

@login_required
def events(request,option): 
  objlist = []
  user = request.user
  options = ["upcoming","attending","past"] 
  view = option

  #handle the date functionality
  day = timedelta(days = 1) 
  today= datetime.date(2011,07,10)
  datelist = []
  #uncomment the below line to bring things up to date
  today = date.today()
  datelist.append([])
  datelist[0].append(today)
  datelist[0].append(today.strftime("%A, %B %d"))
 
  temp = today
  for i in range(1,7,1):
    datelist.append([])
    temp += day
    datelist[i].append(temp)
    datelist[i].append(temp.strftime("%A, %B %d"))

  #upcoming
  if string.lower(option) == options[0] :
    events = get_available_events(user) 
    for element in datelist:
      obj = EventDay()
      obj.date = element[0]
      obj.datestring = element[1]
      temparray = [] 
      count = 0
      for event in events: 
        if event.event_date.strftime("%B %d, %y") == obj.date.strftime("%B %d, %y"): 
          temparray.append(event)
          count = count + 1  
      obj.count = count
      obj.eventlist = temparray
      objlist.append(obj)
  #attending
  elif string.lower(option) == options[1]:
    #avail = get_available_events(user)  
    avail = ActivityBase.objects.filter(type='event')
    attending = []
    
    for event in avail:
      #delete
      #attending.append(event.activity)
      try:
        member = ActivityMember.objects.get(user=request.user,activity=event) 
        if member.approval_status == "pending":
          attending.append(event.activity) 
      except ActivityMember.DoesNotExist: 
          boolean = False
    for element in datelist:
      obj = EventDay()
      obj.date = element[0]
      obj.datestring = element[1]
      count = 0
      temparray = [] 
      for event in attending: 
        if event.event_date.strftime("%B %d, %y") == obj.date.strftime("%B %d, %y"):
          temparray.append(event)
          count = count + 1 
      obj.count = count
      obj.eventlist = temparray
      #obj.eventlist = attending
      objlist.append(obj)
  

  #past
  elif string.lower(option) == options[2]:   
    avail = ActivityBase.objects.filter(type='event')
    for event in avail:
      if event.activity.event_date.date() < today:
        objlist.append(event.activity) 
    objlist.sort(key=get_date)
  return render_to_response("mobile/events/index.html", {
  "view": view, 
  "objlist": objlist,
  "options": options, 
  }, context_instance=RequestContext(request))



@login_required
def quests(request,option): 
  questlist = []
  user = request.user
  options = ["available","accepted","completed"] 
  view = option 

  #completed
  if string.lower(option) == options[2]:
    questlist = Quest.objects.filter(questmember__user=request.user,questmember__completed=True)  

  return render_to_response("mobile/quests/index.html", {
  "view": view,
  "questlist": questlist,
  "options": options, 
  }, context_instance=RequestContext(request))

@login_required
def quest_detail(request, slug):
  quest=get_object_or_404(Quest,quest_slug=slug)  
  return render_to_response("mobile/quests/details.html", {
    "quest": quest,
  }, context_instance=RequestContext(request))

@login_required
def popup(request):
  return render_to_response("mobile/quests/popup.html", {}, context_instance=RequestContext(request))
