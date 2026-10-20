import { AlertCircle, LoaderCircle } from "lucide-react";

export function LoadingSpinner({ label = "Loading data..." }) {
  return (
    <div className="feedback feedback-loading" role="status">
      <LoaderCircle className="spin" size={20} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorMessage({ message, onRetry }) {
  return (
    <div className="feedback feedback-error" role="alert">
      <AlertCircle size={18} aria-hidden="true" />
      <span>{message}</span>
      {onRetry && (
        <button className="text-button" onClick={onRetry} type="button">
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title = "No dataset uploaded", children }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}
