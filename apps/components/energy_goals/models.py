import datetime

from django.db import models
from django.contrib.auth.models import User

from components.floors.models import Floor

# Create your models here.

class EnergyGoal(models.Model):
  start_date = models.DateField(help_text="The date on which the goal starts.  Users will begin voting at 12:00am on this date.")
  voting_end_date = models.DateField(help_text="The date on which voting ends. Voting ends at 12:00am on this date and the goal starts.")
  end_date = models.DateField(help_text="The goal will end at 12:00am on this date.")
  minimum_goal = models.IntegerField(default=0, help_text="The lowest percent reduction possible for a goal.")
  maximum_goal = models.IntegerField(default=50, help_text="The highest percent reduction possible for a goal.")
  goal_increments = models.IntegerField(default=5, help_text="The percent increments users will be able to vote on.")
  default_goal = models.IntegerField(
      default=5, 
      help_text="The default percent reduction that will appear in the voting form." + 
                "This must be a multiple of the goal increments between the minimum and maximum goal."
  )
  point_conversion = models.FloatField(
      default=1.0,
      help_text="The points awarded for this goal will be the percent reduction multiplied by this number.",
  )
  created_at = models.DateTimeField(editable=False, auto_now_add=True)
  updated_at = models.DateTimeField(editable=False, auto_now=True)
  
  def __unicode__(self):
    return "Goal for %s to %s" % (self.start_date, self.end_date)
    
  @staticmethod
  def get_current_goal():
    """Gets the current energy goal. Returns None if no goal is currently going on."""
    today = datetime.date.today()
    for goal in EnergyGoal.objects.all():
      if today >= goal.start_date and today < goal.end_date:
        return goal
        
    return None
    
  def in_voting_period(self):
    """Returns True if the goal is in the voting period and False otherwise."""
    today = datetime.date.today()
    if today >= self.start_date and today < self.voting_end_date:
      return True
    
    return False
    
  def user_can_vote(self, user):
    """Determines if the user can vote."""
    for vote in self.energygoalvote_set.all():
      if vote.user == user:
        return False
        
    return True
    
  def get_floor_results(self, floor):
    """Get the floor's voting results for this goal."""
    votes = self.energygoalvote_set.filter(
      user__profile__floor=floor,
    ).values("percent_reduction").annotate(votes=models.Count('id')).order_by("-votes", "-percent_reduction")
        
    return votes
    
class EnergyGoalVote(models.Model):
  user = models.ForeignKey(User, editable=False)
  goal = models.ForeignKey(EnergyGoal, editable=False)
  percent_reduction = models.IntegerField(default=5)
  created_at = models.DateTimeField(editable=False, auto_now_add=True)
  
  class Meta:
    # Ensures that a user can only vote on a single goal.
    unique_together = ("user", "goal")
    
class FloorEnergyGoal(models.Model):
  floor = models.ForeignKey(Floor)
  goal = models.ForeignKey(EnergyGoal)
  percent_reduction = models.IntegerField(default=0, editable=False)
  completed = models.BooleanField(default=False, help_text="Check this box if the floor has completed the goal.")
  awarded = models.BooleanField(default=False, editable=False)
  
  created_at = models.DateTimeField(editable=False, auto_now_add=True)
  updated_at = models.DateTimeField(editable=False, auto_now=True)
  
  def save(self):
    """Overrided save method to award the goal's points to members of the floor."""
    if self.completed and not self.awarded:
      points = int(self.goal.point_conversion * self.percent_reduction)
      # Subtract a minute from the end date in order to get around energy goals tied to rounds, which
      # also end at midnight.
      # Conversion from http://stackoverflow.com/questions/1937622/convert-date-to-datetime-in-python
      award_date = datetime.datetime.combine(self.goal.end_date, datetime.time()) - datetime.timedelta(minutes=1)
      for profile in self.floor.profile_set.all():
        profile.add_points(points, award_date)
        profile.save()
        
      self.awarded = True
      
    super(FloorEnergyGoal, self).save()
