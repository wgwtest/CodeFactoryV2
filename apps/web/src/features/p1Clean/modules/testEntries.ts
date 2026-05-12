import { intakeTestEntry } from "./intake/testEntry";
import { knowledgeBaseManagementTestEntry } from "./knowledgeBaseManagement/testEntry";
import { knowledgeResultsTestEntry } from "./knowledgeResults/testEntry";
import { policyRulesTestEntry } from "./policyRules/testEntry";
import { publicationTestEntry } from "./publication/testEntry";
import { qualityGraphTestEntry } from "./qualityGraph/testEntry";
import { runtimeTestEntry } from "./runtime/testEntry";
import { systemOutputTestEntry } from "./systemOutput/testEntry";

export const p1ModuleTestEntries = [
  knowledgeBaseManagementTestEntry,
  intakeTestEntry,
  policyRulesTestEntry,
  runtimeTestEntry,
  qualityGraphTestEntry,
  knowledgeResultsTestEntry,
  publicationTestEntry,
  systemOutputTestEntry,
];
