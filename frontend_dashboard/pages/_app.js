import "../styles/globals.css";
import "../styles/auth.css";
import { ToastProvider } from "../components/ToastProvider";

export default function App({ Component, pageProps }) {
  return (
    <ToastProvider>
      <Component {...pageProps} />
    </ToastProvider>
  );
}
