import { cloneElement } from "react";

interface FieldControlProps {
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
  "aria-errormessage"?: string;
}

interface FormFieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactElement<FieldControlProps>;
}

export function FormField({
  id,
  label,
  error,
  hint,
  children,
}: FormFieldProps) {
  const descriptionIds = [hint ? `${id}-hint` : "", error ? `${id}-error` : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={`form-field${error ? " form-field--invalid" : ""}`}>
      <label htmlFor={id}>{label}</label>
      {hint && (
        <span className="form-field__hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
      {cloneElement(children, {
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": descriptionIds || undefined,
        "aria-errormessage": error ? `${id}-error` : undefined,
      })}
      {error && (
        <span className="form-field__error" id={`${id}-error`}>
          {error}
        </span>
      )}
    </div>
  );
}
