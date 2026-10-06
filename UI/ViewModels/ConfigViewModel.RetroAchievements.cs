using CommunityToolkit.Mvvm.ComponentModel;

namespace Mesen.ViewModels
{
	public partial class ConfigViewModel
	{
		[ObservableProperty] public partial RetroAchievementsConfigViewModel? RetroAchievements { get; set; }
	}
}
