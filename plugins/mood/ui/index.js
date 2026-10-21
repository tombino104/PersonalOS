import MoodBlock from './MoodBlock.svelte';
import ReportSection from './ReportSection.svelte';
import TrendPage from './TrendPage.svelte';

export default {
  questionnaireBlocks: { mood: MoodBlock },
  reportSections: { mood: ReportSection },
  pages: { trend: TrendPage },
};
