import { forwardRef } from "react";
import { Button as BaseButton, type ButtonProps } from "@kabisa/ui-web";
import { cn } from "@/lib/utils";
export type { ButtonProps };
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, ...props }, ref) => (
    <BaseButton
      ref={ref}
      variant={variant}
      className={cn(
        "ops-button",
        (!variant || variant === "primary") && "ops-button-primary",
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
