import { BowlGamesEditor } from '../components/index.js';
import { useApp } from '../context/AppContext.jsx';

// Shared postseason editor page. The shell only adds its tab after the custom
// field is selected, and the component owns every rendered shape on the page.
export default function BowlGamesPage() {
  const { toast } = useApp();
  return <BowlGamesEditor toast={toast} />;
}
