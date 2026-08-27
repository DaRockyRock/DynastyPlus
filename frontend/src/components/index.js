// Component library barrel. Pages import everything from here so the app
// always composes from the library rather than ad-hoc markup.

// --- UI primitives ---
export { default as Button } from './ui/Button.jsx';
export { default as RegenerateButton } from './ui/RegenerateButton.jsx';
export { default as Badge } from './ui/Badge.jsx';
export { default as Chip } from './ui/Chip.jsx';
export { default as Card } from './ui/Card.jsx';
export { default as SectionTitle } from './ui/SectionTitle.jsx';
export { default as SourcePill } from './ui/SourcePill.jsx';
export { default as TeamLogo } from './ui/TeamLogo.jsx';
export { default as ConferenceLogo } from './ui/ConferenceLogo.jsx';
export { default as LogoPlate } from './ui/LogoPlate.jsx';
export { default as ReliabilityBar } from './ui/ReliabilityBar.jsx';
export { default as StarRating } from './ui/StarRating.jsx';
export { default as TrendTag } from './ui/TrendTag.jsx';
export { default as StatusTag } from './ui/StatusTag.jsx';
export { default as Avatar } from './ui/Avatar.jsx';
export { default as StatCard } from './ui/StatCard.jsx';
export { default as KeyValue } from './ui/KeyValue.jsx';
export { default as HeatBar } from './ui/HeatBar.jsx';
export { default as NilCallout } from './ui/NilCallout.jsx';
export { default as ProgressBar } from './ui/ProgressBar.jsx';
export { default as Skeleton } from './ui/Skeleton.jsx';
export { default as EmptyState } from './ui/EmptyState.jsx';
export { default as Modal } from './ui/Modal.jsx';
export { default as ConfirmDialog } from './ui/ConfirmDialog.jsx';
export { default as Toast } from './ui/Toast.jsx';
export { default as PullQuote } from './ui/PullQuote.jsx';
export { default as SegmentedControl } from './ui/SegmentedControl.jsx';
export { default as MoneyValue } from './ui/MoneyValue.jsx';
export { default as PointsValue } from './ui/PointsValue.jsx';
export { default as BudgetMeter } from './ui/BudgetMeter.jsx';
export { default as AllocationBar } from './ui/AllocationBar.jsx';
export { default as StageTag } from './ui/StageTag.jsx';
export { default as DealbreakerTag } from './ui/DealbreakerTag.jsx';
export { default as FormField } from './ui/FormField.jsx';
export { default as TextInput } from './ui/TextInput.jsx';
export { default as PasswordInput } from './ui/PasswordInput.jsx';
export { default as Select } from './ui/Select.jsx';
export { default as CodeSnippet } from './ui/CodeSnippet.jsx';
export { default as Callout } from './ui/Callout.jsx';
export { default as Stepper } from './ui/Stepper.jsx';
export { default as StatusDot } from './ui/StatusDot.jsx';
export { default as CountBadge } from './ui/CountBadge.jsx';
export { default as VerifiedBadge } from './ui/VerifiedBadge.jsx';
export * as Icons from './ui/icons.jsx';

// --- Domain ---
export { default as StorySlider } from './domain/StorySlider.jsx';
export { default as StoryWatermark } from './domain/StoryWatermark.jsx';
export { default as ArticleCard } from './domain/ArticleCard.jsx';
export { default as ArticleFull } from './domain/ArticleFull.jsx';
export { default as ArticleReader } from './domain/ArticleReader.jsx';
export { default as QuoteBlock } from './domain/QuoteBlock.jsx';
export { default as StatTable } from './domain/StatTable.jsx';
export { default as BettingCard } from './domain/BettingCard.jsx';
export { default as InsiderReportCard } from './domain/InsiderReportCard.jsx';
export { default as OutletList } from './domain/OutletList.jsx';
export { default as RankingList, RankRow } from './domain/RankingList.jsx';
export { default as ResultCard } from './domain/ResultCard.jsx';
export { default as NextGameCard } from './domain/NextGameCard.jsx';
export { default as MarqueeMatchups } from './domain/MarqueeMatchups.jsx';
export { default as MarqueeGame } from './domain/MarqueeGame.jsx';
export { default as CommitteeMemberCard } from './domain/CommitteeMemberCard.jsx';
export { default as CommitteeBallotModal } from './domain/CommitteeBallotModal.jsx';
export { default as PlayoffBracket, SeedRow, MatchupCard } from './domain/PlayoffBracket.jsx';
export { default as BracketImage } from './domain/BracketImage.jsx';
export { default as RankingsModal } from './domain/RankingsModal.jsx';
export { default as ReceivingVotes } from './domain/ReceivingVotes.jsx';
export { default as ProspectCard } from './domain/ProspectCard.jsx';
export { default as CrystalBallCard } from './domain/CrystalBallCard.jsx';
export { default as VisitCard } from './domain/VisitCard.jsx';
export { default as RumorCard } from './domain/RumorCard.jsx';
export { default as MoveRow } from './domain/MoveRow.jsx';
export { default as ClassGradeCard } from './domain/ClassGradeCard.jsx';
export { default as HeatRow } from './domain/HeatRow.jsx';
export { default as CandidateCard } from './domain/CandidateCard.jsx';
export { default as SearchBlock } from './domain/SearchBlock.jsx';
export { default as AwardBlock } from './domain/AwardBlock.jsx';
export { default as VoterCard } from './domain/VoterCard.jsx';
export { default as MilestoneRow } from './domain/MilestoneRow.jsx';
export { default as LegacyCard } from './domain/LegacyCard.jsx';
export { default as RetroCard } from './domain/RetroCard.jsx';
export { default as CoachingTreeCard } from './domain/CoachingTreeCard.jsx';
export { default as ThreadList } from './domain/ThreadList.jsx';
export { default as DecadeCard } from './domain/DecadeCard.jsx';
export { default as BudgetSummaryBar } from './domain/BudgetSummaryBar.jsx';
export { default as DynastyBlueprintCard } from './domain/DynastyBlueprintCard.jsx';
export { default as RecruitingNilTable } from './domain/RecruitingNilTable.jsx';
export { default as RosterNilTable } from './domain/RosterNilTable.jsx';
export { default as NilOfferEditor } from './domain/NilOfferEditor.jsx';
export { default as GameResultRow } from './domain/GameResultRow.jsx';
export { default as Scoreboard } from './domain/Scoreboard.jsx';
// Game Center (the full box score for the user's last game)
export { default as GameScoreHeader } from './domain/GameScoreHeader.jsx';
export { default as TeamStatComparison } from './domain/TeamStatComparison.jsx';
export { default as BoxScoreTable } from './domain/BoxScoreTable.jsx';
export { default as ScoringSummary } from './domain/ScoringSummary.jsx';
export { default as DriveChart } from './domain/DriveChart.jsx';
export { default as KeyPlaysList } from './domain/KeyPlaysList.jsx';
// Post-game press conference (the interactive interview)
export { default as PresserModal } from './domain/PresserModal.jsx';
export { default as PresserReporterHeader } from './domain/PresserReporterHeader.jsx';
export { default as PresserQuestion } from './domain/PresserQuestion.jsx';
export { default as PresserAnswerInput } from './domain/PresserAnswerInput.jsx';
export { default as PresserTranscript } from './domain/PresserTranscript.jsx';
export { default as PresserBusyOverlay } from './domain/PresserBusyOverlay.jsx';
export { default as ScoreOverrideForm } from './domain/ScoreOverrideForm.jsx';
export { default as NewSeasonForm } from './domain/NewSeasonForm.jsx';
export { default as TeamSelect } from './domain/TeamSelect.jsx';
export { default as SimStatusCard } from './domain/SimStatusCard.jsx';
export { default as RecruitRow } from './domain/RecruitRow.jsx';
export { default as RecruitBoard } from './domain/RecruitBoard.jsx';
export { default as RecruitFilters } from './domain/RecruitFilters.jsx';
export { default as SimControlPanel } from './domain/SimControlPanel.jsx';
export { default as InboxDrainPanel } from './domain/InboxDrainPanel.jsx';
export { default as DynastyCard } from './domain/DynastyCard.jsx';

// --- Layout / shell ---
export { default as TopBar } from './layout/TopBar.jsx';
export { default as PageHeader } from './layout/PageHeader.jsx';
export { default as NavTabs } from './layout/NavTabs.jsx';
export { default as WeekNav } from './layout/WeekNav.jsx';
export { default as LiveStatus } from './layout/LiveStatus.jsx';
export { default as LoadingOverlay } from './layout/LoadingOverlay.jsx';
export { default as SettingsFab } from './layout/SettingsFab.jsx';
export { default as LLMStatusPill } from './layout/LLMStatusPill.jsx';
export { default as SimStatusBadge } from './layout/SimStatusBadge.jsx';
export { default as SimTopBar } from './layout/SimTopBar.jsx';
export { default as PendingActionsBadge } from './layout/PendingActionsBadge.jsx';
export { default as PhoneButton } from './layout/PhoneButton.jsx';

// --- Onboarding / LLM setup ---
export { default as OnboardingHeader } from './onboarding/OnboardingHeader.jsx';
export { default as WelcomeIntro } from './onboarding/WelcomeIntro.jsx';
export { default as ProviderCard } from './onboarding/ProviderCard.jsx';
export { default as ProviderPicker } from './onboarding/ProviderPicker.jsx';
export { default as ConnectionForm } from './onboarding/ConnectionForm.jsx';
export { default as GuideStep } from './onboarding/GuideStep.jsx';
export { default as SetupGuide } from './onboarding/SetupGuide.jsx';
export { default as ConnectionTester } from './onboarding/ConnectionTester.jsx';
export { default as OnboardingFooter } from './onboarding/OnboardingFooter.jsx';

// --- Settings / Customize studio ---
export { default as SettingsIcon } from './settings/SettingsIcon.jsx';
export { default as SettingsHeader } from './settings/SettingsHeader.jsx';
export { default as SettingsNav } from './settings/SettingsNav.jsx';
export { default as SettingsPanel } from './settings/SettingsPanel.jsx';
export { default as SettingsField } from './settings/SettingsField.jsx';
export { default as FieldGrid } from './settings/FieldGrid.jsx';
export { default as ObjectForm } from './settings/ObjectForm.jsx';
export { default as EntityCard } from './settings/EntityCard.jsx';
export { default as EntityList } from './settings/EntityList.jsx';
export { default as ColorField } from './settings/ColorField.jsx';
export { default as StarField } from './settings/StarField.jsx';
export { default as TeamField } from './settings/TeamField.jsx';
export { default as ImageUpload } from './settings/ImageUpload.jsx';
export { default as PersonalitySliders } from './settings/PersonalitySliders.jsx';
export { SettingsMetaProvider, useSettingsMeta } from './settings/SettingsContext.jsx';

// --- People ---
export { default as PersonName } from './people/PersonName.jsx';

// --- Phone ---
export { default as PhoneApp } from './phone/PhoneApp.jsx';
export { default as PhoneFrame } from './phone/PhoneFrame.jsx';
export { default as PhoneTabs } from './phone/PhoneTabs.jsx';
export { default as ContactRow } from './phone/ContactRow.jsx';
export { default as ContactSubtitle } from './phone/ContactSubtitle.jsx';
export { default as UnreadDot } from './phone/UnreadDot.jsx';
export { default as MessageBubble } from './phone/MessageBubble.jsx';
export { default as TypingBubble } from './phone/TypingBubble.jsx';
export { default as PhoneThread } from './phone/PhoneThread.jsx';
export { default as ChatBudgetHeader } from './phone/ChatBudgetHeader.jsx';
export { default as ConvoPeerMeta } from './phone/ConvoPeerMeta.jsx';
export { default as ChatActionBar } from './phone/ChatActionBar.jsx';
export { default as NilOfferSheet } from './phone/NilOfferSheet.jsx';
export { default as RecruitingActionSheet } from './phone/RecruitingActionSheet.jsx';
export { default as OfferReceiptBubble } from './phone/OfferReceiptBubble.jsx';
export { default as RecruitBudgetStrip } from './phone/RecruitBudgetStrip.jsx';

// --- Feed (the phone's social timeline) ---
export { default as PhoneBottomNav } from './phone/PhoneBottomNav.jsx';
export { default as FeedScreen } from './phone/FeedScreen.jsx';
export { default as FeedPostCard } from './phone/FeedPostCard.jsx';
export { default as FeedAuthor } from './phone/FeedAuthor.jsx';
export { default as FeedQuotedPost } from './phone/FeedQuotedPost.jsx';
export { default as FeedRefCard } from './phone/FeedRefCard.jsx';
export { default as FeedEngagementRow } from './phone/FeedEngagementRow.jsx';
export { default as FeedBreakingTag } from './phone/FeedBreakingTag.jsx';
