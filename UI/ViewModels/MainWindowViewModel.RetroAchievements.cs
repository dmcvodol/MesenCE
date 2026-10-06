using Mesen.RetroAchievements;

namespace Mesen.ViewModels
{
	public partial class MainWindowViewModel
	{
		// Keep the native RetroAchievements lifecycle manager alive for the full main-window lifetime.
		private readonly RetroAchievementsManager _retroAchievementsManager = RetroAchievementsManager.Instance;
	}
}
