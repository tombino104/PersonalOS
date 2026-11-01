import BatteryCard from './BatteryCard.svelte';
import ReportSection from './ReportSection.svelte';
import SleepPage from './SleepPage.svelte';

export default {
  pages: { nights: SleepPage },
  reportSections: { night: ReportSection },
  widgets: { battery: BatteryCard },
};
