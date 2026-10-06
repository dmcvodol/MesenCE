using CommunityToolkit.Mvvm.ComponentModel;
using Mesen.Config;

namespace Mesen.ViewModels
{
	public partial class RetroAchievementsConfigViewModel : DisposableViewModel
	{
		[ObservableProperty] public partial RetroAchievementsConfig Config { get; set; }
		[ObservableProperty] public partial RetroAchievementsConfig OriginalConfig { get; set; }

		public RetroAchievementsConfigViewModel()
		{
			Config = ConfigManager.Config.RetroAchievements;
			OriginalConfig = Config.Clone();
		}
	}
}
