import { useEffect } from "react";

const SITE_NAME = "ShiftBridge";

export function PageTitle({ title }: { title: string }) {
  useEffect(() => {
    document.title = `${title} | ${SITE_NAME}`;
  }, [title]);

  return null;
}
