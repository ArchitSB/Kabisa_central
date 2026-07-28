import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, LoaderCircle } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Input } from "@/components/ui/input";
import {
  type AdminUser,
  createAdminUser,
  updateAdminUser,
} from "@/features/admin-users/admin-users-api";
import { listRoles } from "@/features/roles/roles-api";
import { getApiErrorDetail } from "@/lib/api-errors";
import { formatRoleName } from "@/lib/utils";

const passwordSchema = z
  .string()
  .refine((value) => !value || value.length >= 8, "Use at least 8 characters.")
  .refine(
    (value) => new TextEncoder().encode(value).length <= 72,
    "Password must be at most 72 bytes.",
  );

const adminUserSchema = z.object({
  name: z.string().trim().min(1, "Enter the administrator’s name.").max(150),
  email: z.string().trim().email("Enter a valid email address."),
  roleId: z.string().uuid("Select a role."),
  password: passwordSchema,
  isActive: z.boolean(),
});

type AdminUserValues = z.infer<typeof adminUserSchema>;

type AdminUserDrawerProps = {
  trigger: React.ReactNode;
  user?: AdminUser;
};

export function AdminUserDrawer({ trigger, user }: AdminUserDrawerProps) {
  const [open, setOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const queryClient = useQueryClient();
  const editing = Boolean(user);
  const developerAccount = user?.role.name === "super_admin";
  const { data: rolesData } = useQuery({
    queryKey: ["roles"],
    queryFn: listRoles,
    enabled: open,
  });
  const {
    control,
    handleSubmit,
    register,
    reset,
    setError,
    formState: { errors },
  } = useForm<AdminUserValues>({
    resolver: zodResolver(adminUserSchema),
    defaultValues: {
      name: "",
      email: "",
      roleId: "",
      password: "",
      isActive: true,
    },
  });
  const mutation = useMutation({
    mutationFn: (values: AdminUserValues) => {
      const payload = {
        name: values.name,
        email: values.email.toLowerCase(),
        role_id: values.roleId,
        is_active: values.isActive,
        ...(values.password ? { password: values.password } : {}),
      };
      if (user) {
        return updateAdminUser(user.id, payload);
      }
      return createAdminUser(payload);
    },
    onSuccess: async (savedUser) => {
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success(editing ? "Administrator updated" : "Administrator created", {
        description: `${savedUser.name} can access Kabisa as ${formatRoleName(savedUser.role.name)}.`,
      });
      setOpen(false);
    },
    onError: (error) => {
      toast.error(
        editing ? "Could not update administrator" : "Could not create administrator",
        {
          description: getApiErrorDetail(error),
        },
      );
    },
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    reset({
      name: user?.name ?? "",
      email: user?.email ?? "",
      roleId: user?.role.id ?? "",
      password: "",
      isActive: user?.is_active ?? true,
    });
    setShowPassword(false);
  }, [open, reset, user]);

  function onSubmit(values: AdminUserValues) {
    if (!editing && !values.password) {
      setError("password", {
        type: "required",
        message: "Set an initial password for this administrator.",
      });
      return;
    }
    mutation.mutate(values);
  }

  const roles = rolesData?.items.filter((role) => role.name !== "super_admin") ?? [];

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-primary-700">
            Access management
          </p>
          <DrawerTitle>{editing ? "Edit administrator" : "Add administrator"}</DrawerTitle>
          <DrawerDescription>
            {editing
              ? "Update the profile, role, status, or set a new password."
              : "Create an operational account with an initial password and one role."}
          </DrawerDescription>
        </DrawerHeader>

        <form
          id={`admin-user-form-${user?.id ?? "new"}`}
          className="flex flex-1 flex-col"
          onSubmit={handleSubmit(onSubmit)}
          noValidate
        >
          <div className="space-y-5 px-6 py-6">
            <div>
              <label htmlFor="admin-name" className="mb-2 block text-sm font-semibold">
                Full name
              </label>
              <Input
                id="admin-name"
                autoComplete="name"
                aria-invalid={Boolean(errors.name)}
                {...register("name")}
              />
              {errors.name ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.name.message}
                </p>
              ) : null}
            </div>

            <div>
              <label htmlFor="admin-email" className="mb-2 block text-sm font-semibold">
                Email address
              </label>
              <Input
                id="admin-email"
                type="email"
                autoComplete="email"
                disabled={developerAccount}
                aria-invalid={Boolean(errors.email)}
                {...register("email")}
              />
              {errors.email ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.email.message}
                </p>
              ) : developerAccount ? (
                <p className="mt-1.5 text-xs text-secondary">
                  The developer super-admin email is fixed by server configuration.
                </p>
              ) : null}
            </div>

            <div>
              <label htmlFor="admin-role" className="mb-2 block text-sm font-semibold">
                Role
              </label>
              {developerAccount ? (
                <Input id="admin-role" value="Super Admin · Developer" disabled readOnly />
              ) : (
                <select
                  id="admin-role"
                  className="control-base w-full"
                  aria-invalid={Boolean(errors.roleId)}
                  {...register("roleId")}
                >
                  <option value="">Select a role</option>
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {formatRoleName(role.name)}
                    </option>
                  ))}
                </select>
              )}
              {errors.roleId ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.roleId.message}
                </p>
              ) : null}
            </div>

            <div>
              <label htmlFor="admin-password" className="mb-2 block text-sm font-semibold">
                {editing ? "New password" : "Initial password"}
                {editing ? (
                  <span className="font-normal text-muted"> (optional)</span>
                ) : null}
              </label>
              <div className="relative">
                <Input
                  id="admin-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  className="pr-11"
                  aria-invalid={Boolean(errors.password)}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-1 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-lg text-muted transition-colors duration-micro hover:bg-primary-50 hover:text-primary-800"
                >
                  {showPassword ? (
                    <EyeOff aria-hidden="true" className="size-4" />
                  ) : (
                    <Eye aria-hidden="true" className="size-4" />
                  )}
                </button>
              </div>
              {errors.password ? (
                <p className="mt-1.5 text-xs font-medium text-danger">
                  {errors.password.message}
                </p>
              ) : (
                <p className="mt-1.5 text-xs text-secondary">
                  Use 8–72 UTF-8 bytes. Passwords are never returned or logged.
                </p>
              )}
            </div>

            <Controller
              control={control}
              name="isActive"
              render={({ field }) => (
                <label className="flex items-start gap-3 rounded-control border border-border bg-[#FBFCFB] p-4">
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={(value) => field.onChange(Boolean(value))}
                    disabled={developerAccount}
                    aria-label="Administrator can sign in"
                  />
                  <span>
                    <span className="block text-sm font-semibold">Active account</span>
                    <span className="mt-0.5 block text-xs leading-5 text-secondary">
                      Inactive administrators cannot sign in, and existing sessions stop
                      working.
                    </span>
                  </span>
                </label>
              )}
            />
          </div>

          <DrawerFooter>
            <DrawerClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DrawerClose>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <>
                  <LoaderCircle aria-hidden="true" className="animate-spin" />
                  Saving…
                </>
              ) : editing ? (
                "Save changes"
              ) : (
                "Create administrator"
              )}
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
