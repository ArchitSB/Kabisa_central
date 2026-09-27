import { router } from "expo-router";
import { Action, Empty, Screen, t } from "../src/ui";
export default function NotFound() {
  return (
    <Screen>
      <Empty
        title={t("page.notFound")}
        body={t("page.notFoundBody")}
        action={
          <Action
            label={t("page.backHome")}
            onPress={() => router.replace("/")}
          />
        }
      />
    </Screen>
  );
}
