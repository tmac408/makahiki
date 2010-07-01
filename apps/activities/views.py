import datetime

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.forms.util import ErrorList
from django.contrib.contenttypes.models import ContentType

from activities.models import *
from activities.forms import *
from activities import MAX_COMMITMENTS

@login_required
def home(request):
  """Home page listing for activities.  We may want to add top commitments/activities/goals later."""
  return render_to_response('activities/home.html', {}, context_instance = RequestContext(request))

@login_required
def list(request, item_type):
  user = request.user
  
  user_items = available_items = completed_items = item_name = None
  
  if item_type == "activity":
    user_items = user.activity_set.filter(
      activitymember__user=user,
      activitymember__awarded=False,
    )
    available_items = Activity.get_available_for_user(user)
    completed_items = user.activity_set.filter(
      activitymember__user=user,
      activitymember__awarded=True,
    )
    item_name = "activities"
    
  elif item_type == "commitment":
    user_items = user.commitment_set.filter(
      commitmentmember__user=user,
      commitmentmember__completed=False,
    )
    available_items = Commitment.get_available_for_user(user)
    completed_items = user.commitment_set.filter(
      commitmentmember__user=user,
      commitmentmember__completed=True
    )
    item_name = "commitments"
    
  elif item_type == "goal":
    user_items = user.get_profile().floor.goal_set.filter(
      goalmember__floor=user.get_profile().floor,
      goalmember__awarded=False,
    )
    available_items = Goal.get_available_for_user(user)
    completed_items = user.get_profile().floor.goal_set.filter(
      goalmember__floor=user.get_profile().floor,
      goalmember__awarded=True,
    )
    item_name = "goals"
  
  else:
    # Already handled by urls.py, but just to be safe.
    return Http404
    
  return render_to_response('activities/list.html', {
    "user_items": user_items,
    "available_items": available_items,
    "completed_items": completed_items,
    "item_name": item_name,
  }, context_instance = RequestContext(request))
  
@login_required
def like(request, item_type, item_id):
  """Like an activity/commitment/goal."""
  
  user = request.user
  content_type = get_object_or_404(ContentType, app_label="activities", model=item_type.capitalize())
  try:
    like = Like.objects.get(user=user, content_type=content_type, object_id=item_id)
    request.user.message_set.create(message="You already like this item.")
  except ObjectDoesNotExist:
    like = Like(user=user, floor=user.get_profile().floor, content_type=content_type, object_id=item_id)
    like.save()
    
  return HttpResponseRedirect(reverse("activities.views.list", args=(item_type,))) 
  
@login_required
def unlike(request, item_type, item_id):
  """Unlike an activity/commitment/goal."""

  user = request.user
  content_type = get_object_or_404(ContentType, app_label="activities", model=item_type.capitalize())
  try:
    like = Like.objects.get(user=user, content_type=content_type, object_id=item_id)
    like.delete()
  except ObjectDoesNotExist:
    request.user.message_set.create(message="You do not like this item.")

  return HttpResponseRedirect(reverse("activities.views.list", args=(item_type,)))

@login_required
def add_participation(request, item_type, item_id):
  """Adds the user as participating in the item."""
  
  if not request.method == "POST":
    request.user.message_set.create(message="We could not process your request.  Please try again.")
    return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
  elif item_type == "commitment":
    return __add_commitment(request, item_id)
  elif item_type == "activity":
    return __add_activity(request, item_id)
  elif item_type == "goal":
    return __add_goal(request, item_id)
  else:
    raise Http404

@login_required
def remove_participation(request, item_type, item_id):
  """Removes the user's participation in the item."""
  
  if not request.method == "POST":
    request.user.message_set.create(message="We could not process your request.  Please try again.")
    return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
  elif item_type == "commitment":
    return __remove_active_commitment(request, item_id)
  elif item_type == "activity":
    return __remove_activity(request, item_id)
  elif item_type == "goal":
    return __remove_goal(request, item_id)
  else:
    raise Http404
    
@login_required
def request_points(request, item_type, item_id):
  """Request the points for a given item."""

  if item_type == "activity":
    return __request_activity_points(request, item_id)
  elif item_type == "commitment":
    return __request_commitment_points(request, item_id)
  elif item_type == "goal":
    return __request_goal_points(request, item_id)
  else:
    raise Http404
    
@login_required
def view_codes(request, activity_id):
  """View the confirmation codes for a given activity."""
  
  if not request.user or not request.user.is_staff:
    raise Http404
    
  activity = get_object_or_404(Activity, pk=activity_id)
  codes = ConfirmationCode.objects.filter(activity=activity)
  if len(codes) == 0:
    raise Http404
  
  return render_to_response("activities/view_codes.html", {
    "activity": activity,
    "codes": codes,
  }, context_instance = RequestContext(request))

### Private methods.

def __add_commitment(request, commitment_id):
  """Commit the current user to the commitment."""
  
  commitment = get_object_or_404(Commitment, pk=commitment_id)
  user = request.user
  
  # Get the number of active commitments for this user
  active_commitments = Commitment.objects.filter(
    commitmentmember__user__username=user.username,
    commitmentmember__completed=False,
  )    
  if len(active_commitments) == MAX_COMMITMENTS:
    message = "You can only have %d active commitments." % MAX_COMMITMENTS
    user.message_set.create(message=message)
  elif commitment in active_commitments:
    user.message_set.create(message="You are already committed to this commitment.")
  else:
    # User can commit to this commitment.
    member = CommitmentMember(user=user, commitment=commitment)
    member.save()
    user.message_set.create(message="You are now committed to \"%s\"" % commitment.title)
    
  return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))

def __remove_active_commitment(request, commitment_id):
  """Removes a user's active commitment.  Inactive commitments cannot be removed except by admins."""
  
  commitment = get_object_or_404(Commitment, pk=commitment_id)
  user = request.user
  commitment_member = get_object_or_404(CommitmentMember, user=user, commitment=commitment, completed=False)
  
  commitment_member.delete()
  user.message_set.create(message="Commitment \"%s\" has been removed." % commitment.title)
    
  return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))

def __add_activity(request, activity_id):
  """Commit the current user to the activity."""

  activity = get_object_or_404(Activity, pk=activity_id)
  user = request.user

  # Search for an existing activity for this user
  if not ActivityMember.objects.filter(user=user, activity=activity):
    activity_member = ActivityMember(user=user, activity=activity)
    activity_member.save()
    user.message_set.create(message="You are now participating in the activity \"" + activity.title + "\"")
  else:
    return Http404

  return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))

def __remove_activity(request, activity_id):
  """Remove the current user's activity."""

  activity = get_object_or_404(Activity, pk=activity_id)
  user = request.user
  activity_member = get_object_or_404(ActivityMember, user=user, activity=activity)

  activity_member.delete()
  user.message_set.create(message="Your participation in the activity \"" + activity.title + "\" has been removed")
  return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
    
def __add_goal(request, goal_id):
  """Add the goal to the floor."""
  
  goal = get_object_or_404(Goal, pk=goal_id)
  user = request.user
  floor = user.get_profile().floor
  goal_member = GoalMember.objects.filter(floor=floor, goal=goal)
  
  if not goal_member and GoalMember.can_add_goal(user):
    goal_member = GoalMember(user=user, goal=goal, floor=user.get_profile().floor)
    goal_member.save()
    user.message_set.create(message="Your floor is now participating in the goal \"" + goal.title + "\"")
  else:
    return Http404
    
  return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
  
def __remove_goal(request, goal_id):
  goal = get_object_or_404(Goal, pk=goal_id)
  user = request.user
  floor = user.get_profile().floor
  goal_member = get_object_or_404(GoalMember, goal=goal, user=user, floor=floor)
  
  # At this point, user is allowed to remove the goal because they own goal_member
  goal_member.delete()
  user.message_set.create(message="Your floor's participation in \"" + goal.title + "\" has been removed")
  return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
    
def __request_commitment_points(request, commitment_id):
  """Generates a form to add an optional comment."""
  commitment = get_object_or_404(Commitment, pk=commitment_id)
  user = request.user
  membership = None
  
  try:
    membership = CommitmentMember.objects.get(
      user=user, 
      commitment=commitment, 
      completed=False,
      completion_date__lte=datetime.date.today,           
    )
    
  except ObjectDoesNotExist:
    user.message_set.create(message="Either the commitment is not active or it is not completed yet.")
    return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
  
  if request.method == "POST":
    form = CommitmentCommentForm(request.POST)
    if form.is_valid():
      # Currently, nothing in the form needs validation, but just to be safe.
      membership.comment = form.cleaned_data["comment"]
      membership.completed = True
      
      # Note that points are added outside of the model save for simplicity (over consistency).
      profile = user.get_profile()
      profile.points += commitment.point_value
      profile.save()
      membership.save()
      
      message = "You have been awarded %d points for your participation!" % commitment.point_value
      user.message_set.create(message=message)
      return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
    
  form = CommitmentCommentForm()
  return render_to_response("activities/request_commitment_points.html", {
    "form": form,
    "commitment": commitment,
  }, context_instance = RequestContext(request))
    
def __request_activity_points(request, activity_id):
  """Creates a request for points for an activity."""
  
  activity = get_object_or_404(Activity, pk=activity_id)
  user = request.user
  question = None
  activity_member = None
  
  try:
    # Retrieve an existing activity member object if it exists.
    activity_member = ActivityMember.objects.get(user=user, activity=activity)
    if activity_member.awarded:
      user.message_set.create(message="You have already received the points for this activity.")
      return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
      
  except ObjectDoesNotExist:
    pass # Ignore for now.

  if request.method == "POST":
    if activity.confirm_type == "image":
      form = ActivityImageForm(request.POST, request.FILES)
    else:
      form = ActivityTextForm(request.POST)
      
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
        user.message_set.create(message="Your request has been submitted!")
        
      # Attach text prompt question if one is provided
      elif form.cleaned_data.has_key("question"):
        activity_member.question = TextPromptQuestion.objects.get(pk=form.cleaned_data["question"])
        activity_member.response = form.cleaned_data["response"]
        activity_member.approval_status = "pending"
        user.message_set.create(message="Your request has been submitted!")
        
      else:
        # Approve the activity (confirmation code is validated in forms.ActivityTextForm.clean())
        code = ConfirmationCode.objects.get(code=form.cleaned_data["response"])
        code.is_active = False
        code.save()
        activity_member.approval_status = "approved" # Model save method will award the points.
        points = activity_member.activity.point_value
        message = "You have been awarded %d points for your participation!" % points
        user.message_set.create(message=message)

      activity_member.save()
      return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
    
  # Create activity request form.
  elif activity.confirm_type == "image":
    form = ActivityImageForm()
  elif activity.confirm_type == "text":
    question = activity.pick_question()
    form = ActivityTextForm(initial={"question" : question.pk})
  else:
    form = ActivityTextForm()
    
  admin_message = activity_member.admin_comment if activity_member else None
      
  return render_to_response("activities/request_activity_points.html", {
    "form": form,
    "activity": activity,
    "question" : question,
    "admin_message": admin_message,
  }, context_instance = RequestContext(request))
  
def __request_goal_points(request, goal_id):
  """Creates or processes a form for requesting points."""
  
  goal = get_object_or_404(Goal, pk=goal_id)
  user = request.user
  floor = user.get_profile().floor
  goal_member = get_object_or_404(GoalMember, user=user, floor=floor, goal=goal)
  
  if request.method == "POST":
    form = GoalCommentForm(request.POST)
    if form.is_valid():
      goal_member.approval_status = "pending"
      goal_member.user_comment = form.cleaned_data["comment"]
      goal_member.save()
      
      user.message_set.create(message="Your request has been submitted!")
      return HttpResponseRedirect(reverse("makahiki_profiles.views.profile", args=(request.user.username,)))
    
  # Create goal request form.
  else:
    form = GoalCommentForm()
  
  admin_comment = goal_member.admin_comment
  
  return render_to_response("activities/request_goal_points.html", {
    "form": form,
    "goal": goal,
    "admin_comment": admin_comment,
  }, context_instance = RequestContext(request))
  
  
  