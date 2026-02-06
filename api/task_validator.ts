/**
 * Task Validator - Validates tasks before execution
 */

export interface TaskValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface TaskValidationOptions {
  maxCodeLength?: number;
  maxTimeout?: number;
  allowedLanguages?: string[];
  blockedKeywords?: string[];
  requireResourceLimits?: boolean;
}

export class TaskValidator {
  private defaultOptions: TaskValidationOptions = {
    maxCodeLength: 100000, // 100KB
    maxTimeout: 3600, // 1 hour
    allowedLanguages: ['python', 'javascript', 'node', 'bash'],
    blockedKeywords: [
      // System access
      'import os',
      'import sys',
      'subprocess',
      'exec(',
      'eval(',
      '__import__',
      // File system
      'open(',
      'file(',
      // Network
      'socket',
      'urllib',
      'requests',
      'http',
      // Docker escape
      '/proc/',
      '/sys/',
      '/dev/',
      // Dangerous operations
      'rm -rf',
      'format',
      'delete',
    ],
    requireResourceLimits: true,
  };

  /**
   * Validate a task
   */
  validate(
    task: {
      code: string;
      language: string;
      timeout?: number;
      requirements?: any;
    },
    options?: TaskValidationOptions
  ): TaskValidationResult {
    const opts = { ...this.defaultOptions, ...options };
    const errors: string[] = [];
    const warnings: string[] = [];

    // Validate code length
    if (task.code.length > opts.maxCodeLength!) {
      errors.push(
        `Code exceeds maximum length of ${opts.maxCodeLength} characters`
      );
    }

    // Validate language
    if (!opts.allowedLanguages!.includes(task.language.toLowerCase())) {
      errors.push(
        `Language '${task.language}' is not allowed. Allowed: ${opts.allowedLanguages!.join(', ')}`
      );
    }

    // Validate timeout
    if (task.timeout && task.timeout > opts.maxTimeout!) {
      errors.push(`Timeout exceeds maximum of ${opts.maxTimeout} seconds`);
    }

    if (!task.timeout || task.timeout < 1) {
      warnings.push('No timeout specified, using default');
    }

    // Check for blocked keywords
    const codeLower = task.code.toLowerCase();
    for (const keyword of opts.blockedKeywords!) {
      if (codeLower.includes(keyword.toLowerCase())) {
        errors.push(`Code contains blocked keyword: ${keyword}`);
      }
    }

    // Validate resource requirements
    if (opts.requireResourceLimits) {
      if (!task.requirements || Object.keys(task.requirements).length === 0) {
        warnings.push('No resource requirements specified');
      } else {
        // Validate CPU limits
        if (task.requirements.cpu) {
          const cpuCores = task.requirements.cpu.cores || task.requirements.cpu;
          if (typeof cpuCores === 'number' && cpuCores > 16) {
            warnings.push('CPU cores requested exceeds recommended limit (16)');
          }
        }

        // Validate memory limits
        if (task.requirements.memory) {
          const memoryGB =
            task.requirements.memory.totalGB || task.requirements.memory;
          if (typeof memoryGB === 'number' && memoryGB > 32) {
            warnings.push('Memory requested exceeds recommended limit (32GB)');
          }
        }

        // Validate GPU limits
        if (task.requirements.gpu) {
          const gpuCount =
            task.requirements.gpu.count || task.requirements.gpu;
          if (typeof gpuCount === 'number' && gpuCount > 4) {
            warnings.push('GPU count requested exceeds recommended limit (4)');
          }
        }
      }
    }

    // Language-specific validation
    this.validateLanguageSpecific(task.code, task.language, errors, warnings);

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Language-specific validation
   */
  private validateLanguageSpecific(
    code: string,
    language: string,
    errors: string[],
    warnings: string[]
  ): void {
    const lang = language.toLowerCase();

    if (lang === 'python') {
      // Check for dangerous imports
      const dangerousImports = [
        'os',
        'sys',
        'subprocess',
        'ctypes',
        'multiprocessing',
      ];
      for (const imp of dangerousImports) {
        if (code.includes(`import ${imp}`) || code.includes(`from ${imp}`)) {
          errors.push(`Dangerous import detected: ${imp}`);
        }
      }

      // Check for file operations
      if (code.includes('open(') || code.includes('file(')) {
        errors.push('File operations are not allowed');
      }
    }

    if (lang === 'javascript' || lang === 'node') {
      // Check for dangerous Node.js modules
      const dangerousModules = [
        'child_process',
        'fs',
        'os',
        'net',
        'http',
        'https',
      ];
      for (const mod of dangerousModules) {
        if (
          code.includes(`require('${mod}')`) ||
          code.includes(`require("${mod}")`)
        ) {
          errors.push(`Dangerous module detected: ${mod}`);
        }
      }

      // Check for eval
      if (code.includes('eval(') || code.includes('Function(')) {
        errors.push('Dynamic code execution is not allowed');
      }
    }

    if (lang === 'bash') {
      // Check for dangerous commands
      const dangerousCommands = ['rm', 'dd', 'mkfs', 'fdisk', 'format'];
      for (const cmd of dangerousCommands) {
        if (new RegExp(`\\b${cmd}\\b`).test(code)) {
          errors.push(`Dangerous command detected: ${cmd}`);
        }
      }
    }
  }

  /**
   * Sanitize code (remove dangerous patterns)
   */
  sanitize(code: string, language: string): string {
    let sanitized = code;

    // Remove comments that might contain dangerous code
    if (language === 'python') {
      // Remove single-line comments
      sanitized = sanitized.replace(/#.*$/gm, '');
    } else if (language === 'javascript' || language === 'node') {
      // Remove single-line and multi-line comments
      sanitized = sanitized.replace(/\/\/.*$/gm, '');
      sanitized = sanitized.replace(/\/\*[\s\S]*?\*\//g, '');
    }

    return sanitized;
  }
}
